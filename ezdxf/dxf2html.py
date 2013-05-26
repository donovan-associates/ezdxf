# Purpose: Create a structured HTML view of the DXF tags - not a CAD drawing!
# Created: 20.05.13
# Copyright (C) 2013, Manfred Moitzi
# License: MIT License
"""Creates a structured HTML view of the DXF tags - not a CAD drawing!
"""

import sys
import os
import shutil
from ezdxf import readfile
from ezdxf.tags import tag_type
from ezdxf.c23 import escape, ustr

HTML_FILE_DEPENDENCIES = ("dxf2html.css", "dxf2html.js")

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="dxf2html.css">
<script src="dxf2html.js"></script>
<title>{name}.dxf</title>
</head>
<body>
<h1>DXF-FILE: {name}.dxf</h1>
<div id="toc">
{toc}
<div>
<div id="dxf-file">
{dxf_file}
</div>
</body>
"""
# Handle definitions
_HANDLE_CODES = [5, 105]
_HANDLE_CODES.extend(range(320, 330))
HANDLE_DEFINITIONS = frozenset(_HANDLE_CODES)

# Handle links
_HANDLE_POINTERS = list(range(330, 370))
_HANDLE_POINTERS.extend((480, 481, 1005))
HANDLE_LINKS = frozenset(_HANDLE_POINTERS)

# Tag groups
GENERAL_MARKER = 0
SUBCLASS_MARKER = 100
APP_DATA_MARKER = 102
EXT_DATA_MARKER = 1001
GROUP_MARKERS = (GENERAL_MARKER,SUBCLASS_MARKER, APP_DATA_MARKER, EXT_DATA_MARKER)
MARKER_TEMPLATE = '<div class="tag-group-marker">{tag}</div>'

TAG_TEMPLATE = '<div class="dxf-tag"><span class="tag-code">{code}</span> <span class="var-type">{type}</span> <span class="tag-value">{value}</span></div>'
TAG_TEMPLATE_HANDLE_DEF = '<div class="dxf-tag"><span id="{value}" class="tag-code">{code}</span> <span class="var-type">{type}</span> <span class="tag-value">{value}</span></div>'
TAG_TEMPLATE_HANDLE_LINK = '<div class="dxf-tag"><span class="tag-code">{code} {type}</span> <a class="tag-value" href="#{value}">{value}</a></div>'
ENTITY_TEMPLATE = '<div class="dxf-entity"><h3>{name}</h3>\n{tags}\n</div>'
TOC_ENTRY_TPL = '<li><a href="#{link}" >{name}</a></li>'
TOC_TPL = '<h2>Table of Contents</h2>\n<ul>\n{}\n</ul>'

def dxf2html(dwg):
    """ Creates a structured HTML view of the DXF tags - not a CAD drawing!
    """
    def get_name():
        if dwg.filename is None:
            return "unknown"
        else:
            filename = os.path.basename(dwg.filename)
            return os.path.splitext(filename)[0]
    dxf_file = sections2html(dwg)
    toc = sections_toc_as_html(dwg)
    return HTML_TEMPLATE.format(name=get_name(), dxf_file=dxf_file, toc=toc)

def sections2html(dwg):
    sections_html = []
    for index, section in enumerate(dwg.sections):
        section_template = create_section_html_template(section.name, index)
        sections_html.append(section2html(section, section_template))
    return '<div class="dxf-sections">\n{}\n</div>'.format("\n".join(sections_html))

def sections_toc_as_html(dwg):
    toc_entries = []
    for index, section in enumerate(dwg.sections):
        toc_entries.append(TOC_ENTRY_TPL.format(
            name=section.name.upper(),
            link=SECTION_ID.format(index)
        ))
    return TOC_TPL.format('\n'.join(toc_entries))

def section2html(section, section_template):
    if section.name == 'header':
        return section_template.format(hdrvars2html(section.hdrvars))
    elif section.name in ('classes', 'objects', 'entities'):
        return section_template.format(entities2html(iter(section)))
    elif section.name == 'tables':
        return section_template.format(tables2html(section))  # no iterator
    elif section.name == 'blocks':
        return section_template.format(blocks2html(iter(section)))
    else:
        return section_template.format(tags2html(section.tags))

SECTION_ID = "section_{}"
def create_section_html_template(name, index):
    def nav_ids():
        return SECTION_ID.format(index-1), SECTION_ID.format(index), SECTION_ID.format(index+1)
    prev_id, this_id, next_id = nav_ids()
    return '<div id="{this_id}" class="dxf-section"><h2>SECTION: {name}</h2>\n<div><a href="#{prev_id}">previous</a> ' \
           '<a href="#{next_id}">next</a></div>\n{{}}\n</div>\n'.format(
        name=name.upper(),
        this_id=this_id,
        prev_id=prev_id,
        next_id=next_id)

TAG_TYPES = {
    int: '<int>',
    float: '<float>',
    ustr: '<str>',
}

def tag_type_str(code):
    return TAG_TYPES[tag_type(code)]

def hdrvars2html(hdrvars):
    def var2str(hdrvar):
        if hdrvar.ispoint:
            return  ustr(hdrvar.getpoint())
        else:
            return ustr(hdrvar.value)

    def vartype(hdrvar):
        if hdrvar.ispoint:
            dim = len(hdrvar.getpoint()) - 2
            return ("<point 2D>", "<point 3D>")[dim]
        else:
            return tag_type_str(hdrvar.code)


    varstrings = [
        TAG_TEMPLATE.format(code=name, value=escape(var2str(value)), type=escape(vartype(value)))
        for name, value in hdrvars.items()
    ]
    return '<div id="dxf-header" class="dxf-header">\n{}\n</div>'.format("\n".join(varstrings))

def tags2html(tags):
    def tag2html(tag):
        tpl = TAG_TEMPLATE
        if tag.code in HANDLE_DEFINITIONS: # is handle definition
            tpl = TAG_TEMPLATE_HANDLE_DEF
        elif tag.code in HANDLE_LINKS: # is handle link
            tpl = TAG_TEMPLATE_HANDLE_LINK
        return tpl.format(code=tag.code, value=escape(ustr(tag.value)), type=escape(tag_type_str(tag.code)))

    def group_marker(tag, tag_html):
        return tag_html if tag.code not in GROUP_MARKERS else MARKER_TEMPLATE.format(tag=tag_html)

    tag_strings = (group_marker(tag, tag2html(tag)) for tag in tags)
    return '<div class="dxf-tags">\n{}\n</div>'.format('\n'.join(tag_strings))

def entities2html(entities):
    entity_strings = (entity2html(entity) for entity in entities)
    return '<div class="dxf-entities">\n{}\n</div>'.format("\n".join(entity_strings))

def entity2html(entity):
    return ENTITY_TEMPLATE.format(name=entity.dxftype(), tags=tags2html(entity.tags))

def tables2html(tables):
    navigation = create_table_navigation(tables)
    tables_html_strings = [table2html(table, navigation) for table in tables]
    return '<div id="dxf-tables" class="dxf-tables">{}</div>'.format('\n'.join(tables_html_strings))

#TODO: table navigation bar
def create_table_navigation(table_section):
    return ''

def table2html(table, navigation=''):
    header = ENTITY_TEMPLATE.format(name="TABLE HEADER", tags=tags2html(table._table_header))
    entries = entities2html(table)
    return '<div class="dxf-block">\n<h2>{name}</h2>\n{nav}\n{header}\n{entries}\n</div>'.format(
        name=table.name.upper(),
        nav= navigation,
        header=header,
        entries=entries)

def blocks2html(blocks):
    block_strings = (block2html(block) for block in blocks)
    return '<div id="dxf-blocks" class="dxf-blocks">\n{}\n</div>'.format('\n'.join(block_strings))

def block2html(block_layout):
    block_html = entity2html(block_layout.block)
    entities_html = entities2html(iter(block_layout))
    endblk_html = entity2html(block_layout.endblk)
    return '<div class="dxf-block">\n<h2>{name}</h2>\n{block}\n{entities}\n{endblk}\n</div>'.format(
        name=block_layout.name, block=block_html, entities=entities_html ,endblk=endblk_html)

def copy_html_dependencies_to(dst_path):
    src_path = os.path.dirname(__file__)
    for filename in HTML_FILE_DEPENDENCIES:
        src = os.path.join(src_path, filename)
        dst = os.path.join(dst_path, filename)
        shutil.copy(src, dst)

if __name__ == "__main__":
    dwg = readfile(sys.argv[1])
    copy_html_dependencies_to(os.path.dirname(dwg.filename))
    html_filename = os.path.splitext(dwg.filename)[0] + '.html'
    with open(html_filename, mode='wt') as fp:
        fp.write(dxf2html(dwg))