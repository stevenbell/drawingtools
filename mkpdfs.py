#!/usr/bin/env python3

# Convert an Inkscape SVG file into a set of PDF slides for presentation
# or printing.
#
# Requires inkscape and pdftk to be installed and in the PATH.
#
# Inspired by mkpdfs.rb (https://gist.github.com/emk/961877)
# Steven Bell <botsnlinux@gmail.com>
#
# By default, each layer in the SVG file produces one slide.
# Layers are ordered from bottom to top (i.e., the bottom layer is the first slide).
# A layer whose name begins with '+' will be added to the previous layer
# A layer whose name begins with '_' will be used as a "base" layer for all
#   slides that follow.
# A layer whose name begins with '.' will always be hidden.  This is useful for
#   guides, templates, or just hiding things that aren't finished.
# There are a set of special tags that will get filled in when placed in a text
# field as ${tag}.  Currently the only tag is ${slide}, which inserts the slide
# number.  This only works for normal text fields, not text boxes.

# To create n-up slides from this, do:
# pdfjam --nup 2x2 --landscape --scale 0.85 --delta '10mm 10mm' --outfile slide_pages.pdf slides.pdf [ranges]

from lxml import etree
import os
from sys import argv

def delete_temporary_files():
  os.system("rm -f " + tempsvg)
  os.system("rm -f slide-*.pdf")

# Configuration
if len(argv) < 2:
  print("Incorrect number of arguments")
  print("Usage: mkpdfs.py SVGFILE\n")
  exit()

srcfile = argv[1]
tmpdir = '.'
tempsvg = 'temp.svg'
coalesce_animations = False # Whether to flatten animations for printouts

delete_temporary_files()

# Load the file and get the namespaces
doc = etree.fromstringlist(open(srcfile)).getroottree()
ns = doc.getroot().nsmap
layers = doc.findall('/svg:g[@inkscape:groupmode="layer"]', namespaces=ns)

# Find all the text strings that we're going to have to replace
texts = doc.findall('//tspan', namespaces=ns)
subst_elements = [] # Text elements where we have to substitute something
subst_strings = [] # The corresponding strings of text

for t in texts:
  if t.text != None and t.text.find('${slide}') != -1:
    subst_elements.append(t)
    subst_strings.append(t.text)

# Hide everything to start; we'll enable layers one at a time for export
# This ensures that even layers we skip below (e.g., hidden layers) will be hidden
for l in layers:
  l.attrib['style'] = 'display:none'

# Remove any hidden layers from our list to process
layers[:] = [l for l in layers if l.attrib['{http://www.inkscape.org/namespaces/inkscape}label'][0] != '.']

# Make all of the layers invisible,
# and find the last layer which should be visible
last_visible_layer = None
for l in layers:
  l.attrib['style'] = 'display:none'
  label = l.attrib['{http://www.inkscape.org/namespaces/inkscape}label']
  if label[0] != '_':
    last_visible_layer = l

# Main pass:
# Build up the layers and create files
slide_num = 0 # Number that we put into slides
page_count = 0 # Used to name the PDF files we export

base_layers = [] # Layers which are always shown once added
visible_layers = [] # Layers visible at the current point in time

for i,l in enumerate(layers):
  label = l.attrib['{http://www.inkscape.org/namespaces/inkscape}label']
  if label[0] == '_':
    # Base layer, add it to the list but don't make a slide for it
    base_layers.append(l)
    continue
  elif label[0] == '+':
    # Additive layer, just append it to the current list
    visible_layers.append(l);
  else:
    # Normal case, reset all the layers and add this one
    visible_layers = base_layers + [l];
    slide_num += 1

  if coalesce_animations and l != last_visible_layer:
    next_label = layers[i+1].attrib['{http://www.inkscape.org/namespaces/inkscape}label']
    if next_label[0] == '+' or next_label[0] == '.':
      # Then don't render just yet
      print("Flattening layer '{}'".format(label))
      continue

  for vl in visible_layers:
    vl.attrib['style'] = 'display:inline'

  # Do the string substitutions
  for s in range(len(subst_elements)):
    subst_elements[s].text = subst_strings[s].replace('${slide}', str(slide_num))

  # Save the updated SVG file
  doc.write(tmpdir + os.path.sep + tempsvg)

  # Call Inkscape to render it
  pdf_name = tmpdir + os.path.sep + "slide-{:03d}.pdf".format(page_count)
  page_count += 1

  print("Exporting '{id}' to {name}".format(id=label, name=pdf_name))
  os.system("inkscape -o {path} --export-area-page {temp}".format(path=pdf_name, temp=tempsvg))

  # Restore things back to the way they were for the next run
  for vl in visible_layers:
    vl.attrib['style'] = 'display:none'

# Merge everything using pdftk
out_path = srcfile[:-4] + '.pdf'
if os.system("pdftk slide-*.pdf cat output {}".format(out_path)):
  print("Failed to combine pdfs!  Check that pdftk is installed")
else:
  print("Output written to {}".format(out_path))

delete_temporary_files()
