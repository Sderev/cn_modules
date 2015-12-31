#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import logging
import shutil

from lxml import etree
from lxml import html
from yattag import indent
from yattag import Doc
from lxml.html.clean import Cleaner

import utils

def write_iframe_code(video_link):
    return '<p><iframe allowfullscreen="" mozallowfullscreen="" webkitallowfullscreen="" data-src="'+video_link+'"></iframe></p>'
    

def parse_content(href, module, outModuleDir, rewrite_iframe_src=True):
    """ open file and replace media links and src for iframes """
    try:
        with open(href, 'r') as file:
            htmltext = file.read()
    except Exception as e:
        logging.exception("Exception reading %s: %s " % (href,e))
        return ''

    if not htmltext:
        return ''
    
    tree = html.fromstring(htmltext)
    # Rewrite image links: for each module file, media dir is one step above (../media/)
    # with html export, medias are accessed from index.html in root dir, so we have 
    # to reconstruct the whole path
    try:
        for element, attribute, link, pos in tree.iterlinks():
            newlink = link.replace("media", module+"/media")
            element.set(attribute, newlink)
    except Exception as e:
        logging.exception("Exception rewriting/removing links %s" % e)

    return html.tostring(tree, encoding='utf-8').decode('utf-8')

def generateMenuSubsections(idSection, subsections,doc,tag,text):
    # looping through subsections, skipping non html files
    for idSubSection, subsection in enumerate(subsections):
        # 1st subsection active by default
        if idSubSection == 0:
            active_sub = " active"
        else:
            active_sub = ""
        subsection_id = "subsec_"+str(idSection)+'_'+str(idSubSection)
        if subsection['folder'] != 'correction':
            with tag('a', href="#", data_sec_id=subsection_id, klass="subsection "+subsection['folder']+active_sub):
                text(str(idSection+1)+'.'+str(idSubSection+1)+' '+
                     subsection['title'])


def generateMenuSections(data,doc,tag,text): 
    for idSection, section in enumerate(data["sections"]):
        # 1st section active by default
        if idSection == 0:
            active_sec = " active"
            display = " display:block"
        else:
            active_sec = ""
            display = ""
        section_id = "sec_"+str(idSection)
        with tag('li'):
            with tag('a', href="#", data_sec_id=section_id, klass="section"+active_sec):
                text(section['num']+' '+section['title'])
            with tag('p', style=display):
                generateMenuSubsections(idSection,section['subsections'],doc,tag,text)

def generateVideo(doc,tag,text,videos,display,subsection,subsec_text):
    for idVid, video in enumerate(videos):
        # go now line for each video after 1st video
        if idVid > 0:
            doc.asis('<br />')
        # add iframe code
        iframe_code = write_iframe_code(video['video_link'])
        if display: # for very first subsection, keep normal iframe src 
            iframe_code = iframe_code.replace('data-src', 'src')
        doc.asis(iframe_code)
        doc.asis("\n\n")
        # add text only 1st time
        if idVid == 0:
            # add text in fancybox lightbox

            text_id = subsection['num']+"_"+str(idVid)
            with tag('div', klass="inline fancybox", href="#"+text_id):
                text('Version Texte du cours')
                with tag('div', klass="mini-text"):
                    doc.asis(subsec_text)
            with tag('div', style="display:none"):
                with tag('div', id=text_id, klass="fancy-text"):
                    doc.asis(subsec_text)

def generateMainContent(data, doc,tag,text,module, outModuleDir):
    # Print main content
    doc.asis('<!--  MAIN CONTENT -->')
    with tag('main', klass="content"):
        # Loop through sections
        for idSection,section in enumerate(data["sections"]):
            
#            section_id = "sec_"+str(idSection)
#            href = os.path.join(module_folder, section['filename'])
#            with tag('section', id=section_id, style=("display:none")):
#                doc.asis(parse_content(href, module_folder))
            # Loop through subsections
            for idSubsection,subsection in enumerate(section['subsections']):
                if subsection['folder'] != 'correction':
                    # load 1st subsec by default, rest is hidden
                    if idSubsection==0 and idSection == 0:
                        display = "true"
                    else:
                        display = "none"
                    subsection_id = "subsec_"+str(idSection)+'_'+str(idSubsection)
                    with tag('section', id=subsection_id, style="display:"+display):
                        # fil d'arianne
                        with tag('p', klass='fil_ariane'):
                            text(section['title']+' | '+subsection['title'])
                        href = os.path.join(outModuleDir, subsection['folder'],subsection['filename'])
                        subsec_text = parse_content(href, module, outModuleDir)
                        if "videos" in subsection and len(subsection["videos"]) != 0 :
                            generateVideo(doc,tag,text,subsection["videos"],display,subsection,subsec_text)
                        else: # print subsection text asis                        
                            if href.endswith(".html"):
                                doc.asis(subsec_text)


def writeHtml(module, outModuleDir,doc):
    module_file_name = os.path.join(outModuleDir, module)+'.html'
    moduleHtml = open(module_file_name, 'w')
    moduleHtml.write(indent(doc.getvalue()))
    moduleHtml.close()
    # Copy the media subdir if necessary to the dest 
    mediaDir = os.path.join(module,"media")
    if os.path.isdir(mediaDir):
        try :
            shutil.copytree(mediaDir, os.path.join(outModuleDir,'media'))
        except FileExistsError as exception:
            logging.warn("%s already exists",mediaDir)
    
def generateModuleHtml(data, module, outModuleDir):
    """ parse data from config file 'moduleX.config.json' and generate a moduleX html file """

    # create magic yattag triple
    doc, tag, text = Doc().tagtext()

    doc.asis('<!--  NAVIGATION MENU -->')
    with tag('nav', klass="menu accordion"):
        with tag('h3'):
            text(data["title"])
        with tag('ul'):
            generateMenuSections(data,doc,tag,text)
            
    generateMainContent(data,doc,tag,text,module, outModuleDir)
    writeHtml(module, outModuleDir,doc)

def processModule(module,e,outDir):
    # generate config file
    utils.processModule(module,outDir)
    outModuleDir = os.path.join(outDir,module)
    # config file for each module is named [module_folder].config.json
    mod_config = os.path.join(outModuleDir, module+'.config.json')
    with open(mod_config, encoding='utf-8') as mod_data_file:
        # load module data from filin
        mod_data = json.load(mod_data_file)
        if 'menutitle' in mod_data:
            shortTitle = mod_data['menutitle']
        else:
            shortTitle = mod_data['title']
        strhtml = '<li><a href="'+module+'/'+module+'.html">'+shortTitle+'</a></li>'

    generateModuleHtml(mod_data, module, outModuleDir)
        
    e.append(html.fromstring(strhtml))
    
def processConfig(fconfig,e,outDir):
    global_data = json.load(fconfig)
    for module in global_data["modules"]:
        processModule(module['folder'],e,outDir)
                      
def processModules(modules,e,outDir):
    for module in modules:
        logging.info("Process %s",module)
        processModule(module,e,outDir)

def processDefault(e,outDir):
    import glob
    listt = glob.glob("module[0-9]")
    for module in sorted(listt,key=lambda a: a.lstrip('module')):
        processModule(module,e,outDir)


def loadTemplate(template="index.tmpl"):
    parser = etree.HTMLParser()
    tree   = etree.parse(template, parser)
    e_list = tree.xpath("//ul[@id='static-nav']")
    return tree,e_list[0]

def prepareDestination(outDir):
    """ Create outDir and copy mandatory files""" 
    if not os.path.isdir(outDir):
       if not os.path.exists(outDir):
           os.makedirs(outDir)
       else:
           print ("Cannot create ",outDir, file=sys.stderr)
           sys.exit(1)
    shutil.copy('accueil.html',os.path.join(outDir,'accueil.html'))
    for d in ['js', 'img', 'svg', 'css']:
        dest = os.path.join(outDir,d)
        try :
            shutil.copytree(d, dest)
        except FileExistsError as e:
            logging.warn("%s already exists",d)
            
############### main ################
if __name__ == "__main__":

    
    import argparse
    parser = argparse.ArgumentParser(description="Parses markdown files and generates a website. Default is to process all folders 'module*'.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-c", "--config",help="config file in a json format",type=argparse.FileType('r'))
    group.add_argument("-m", "--modules",help="module folders",nargs='*')
    parser.add_argument("-l", "--log", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Set the logging level", default='WARNING')
    parser.add_argument("-d", "--destination", help="Set the destination dir", default='build')
    
    args = parser.parse_args()
    logging.basicConfig(filename='toHTML.log',filemode='w',level=getattr(logging, args.logLevel))

    # load the html template
    index,e = loadTemplate();

    # check destination
    prepareDestination(args.destination)
        
    
    if args.config != None:
        processConfig(args.config,e,args.destination)
    elif args.modules != None:
        processModules(args.modules,e,args.destination)
    else:
        processDefault(e,args.destination)

    index.write(os.path.join(args.destination, "index.html"),method='html')    