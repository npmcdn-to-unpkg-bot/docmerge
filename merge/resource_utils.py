import os
import time
import pytz
import iso8601
import datetime
import zipfile
from .config import install_name, remote_library
from .gd_resource_utils import (folder, folder_contents, exportFile, getFile, folder_item, file_content_as, 
        gd_folder_files, gd_path_equivalent)

## Local Resource management

def get_working_dir():
    cwd = os.getcwd()
    if (cwd.find("home")>=0):  
        cwd = os.path.join(cwd,install_name)
    if (cwd.find("scripts")>=0):  
        cwd = cwd.replace("\scripts","")
    return cwd

def strip_xml_dec(content):
    xml_dec_start = content.find("<?xml")
    if xml_dec_start>=0:
        return content[content.find(">")+1:]
    else:
        return content

def get_local_dir(local):
    cwd = get_working_dir()
    if (cwd.find("home")>=0):  
        local_d = "/home/docmerge/"+install_name+"/merge/"+local
    else:  
        local_d = "C:\\Users\\Andrew\\Documents\\GitHub\\docmerge\\merge\\"+local
    return local_d

def get_output_dir():
    return get_local_dir("output")

def get_local_txt_content(cwd, data_folder, data_file):
    try:
        full_file_path = os.path.join(cwd, "merge", data_folder, data_file)
        with open(cwd+"/merge/"+data_folder+"/"+data_file, "r") as file:
            return  file.read()
    except FileNotFoundError:
        return None

def push_local_txt(cwd, data_folder, data_file, payload):
    full_file_path = os.path.join(cwd, "merge", data_folder, data_file)
    return push_local_txt_fullname(full_file_path, payload)

def push_local_txt_fullname(full_file_path, payload):
#    full_file_path = data_file
    with open(full_file_path, "w") as file:
        file.write(payload)
        file.close()
    return full_file_path

def del_local(cwd, data_folder, data_file):
    full_file_path = os.path.join(cwd, "merge", data_folder, data_file)
    os.remove(full_file_path)

def local_folder_files(path, parent='root', mimeType='*', fields="nextPageToken, files(id, name, mimeType, parents"):
    cwd = get_working_dir()
    full_path = os.path.join(cwd, "merge", path)
    files = os.listdir(full_path)
    response = []
    for file in files:
        ext = os.path.splitext(file)[-1].lower()
#        print(file)
#        print(os.path.isfile(os.path.join(full_path, file)))
#        print(os.path.isdir(os.path.join(full_path, file)))
        response.append({
            "name":file, 
            "ext":ext, 
            "isdir": os.path.isdir(os.path.join(full_path, file)),
            "mtime": pytz.utc.localize(datetime.datetime.utcfromtimestamp(os.path.getmtime(os.path.join(full_path, file))))})
    return response



# Remote <-> Local methods


def combined_folder_files(path, parent='root', mimeType='*', fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime)"):
    local_files = local_folder_files(path, parent='root', mimeType='*', fields=fields)
    combined_files = {}
    response = []
    for file in local_files:
        file["is_local"]="Y"
        if remote_library:
            file["is_remote"]="N"
        else:
            file["is_remote"]="X"
        combined_files[file["name"]]=file
    if remote_library:
        remote_files = gd_folder_files(gd_path_equivalent(path), parent='root', mimeType='*', fields="nextPageToken, files(id, name, mimeType, parents, modifiedTime)")
        for file in remote_files:
            if file["name"] in combined_files.keys():
                combined_files[file["name"]]["mimeType"]=file["mimeType"]
            else:
                combined_files[file["name"]]=file
                combined_files[file["name"]]["is_local"]="N"
            combined_files[file["name"]]["is_remote"]="Y"
            print(file)
            combined_files[file["name"]]["modifiedTime"]=iso8601.parse_date(file["modifiedTime"])
            if "mtime" in combined_files[file["name"]].keys():
                if combined_files[file["name"]]["modifiedTime"] > combined_files[file["name"]]["mtime"]: #remote time > local time:
                    combined_files[file["name"]]["is_local"]="R"
            combined_files[file["name"]]["isdir"]=file["mimeType"]=="application/vnd.google-apps.folder"
            combined_files[file["name"]]["ext"] = os.path.splitext(file["name"])[-1].lower()
    for file in combined_files.values():
        response.append(file)
    return response


def refresh_files(path, local_dir, parent='root', mimeType='*', fields="nextPageToken, files(id, name, mimeType, parents)"):
    foldr = folder(path, parent)
    files = folder_contents(foldr["id"], mimeType=mimeType, fields=fields)
    files_info=[]
    for file in files:
        doc_id =file["id"]
        cwd = get_working_dir()
        localFileName = cwd+"/merge/"+local_dir+"/"+file["name"]
        if file["mimeType"] == 'application/vnd.google-apps.folder':
            pass
        elif file["mimeType"] == 'application/vnd.google-apps.document':
            if localFileName.find(".") < 0: # no extension
                files_info.append(exportFile(doc_id, localFileName+".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
            else:
                files_info.append(exportFile(doc_id, localFileName, "text/plain"))
        else:
            files_info.append(getFile(doc_id, localFileName, file["mimeType"]))
    return files_info


    
def folder_file(path, name, parent='root', mimeType='*'):
    foldr = folder(path, parent)
    return folder_item(foldr["id"], name, mimeType=mimeType)

def get_remote_txt_content(data_folder, data_file):
    data_doc_id = folder_file(data_folder, data_file)["id"]
    doc_txt = file_content_as(data_doc_id)
    return doc_txt

def get_txt_content(local_data_folder, remote_data_folder, data_file):
#    print("looking locally")
    content = get_local_txt_content(get_working_dir(), local_data_folder, data_file)
    if content == None:
#        print("looking remotely")
        content = get_remote_txt_content(remote_data_folder, data_file)
    return content

def get_xml_content(local_data_folder, remote_data_folder, data_file):
    content = get_txt_content(local_data_folder, remote_data_folder, data_file)
    if type(content) is bytes:
        content = content.decode("UTF-8")
    return strip_xml_dec(content)

def zip_local_dirs(path, zip_file_name, selected_subdirs = ["templates", "flows", "transforms", "test_data", "branding"]):
    zip_name = os.path.join(path,zip_file_name+".zip")
    ziph = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(path):
        for file in files:
            relpath = os.path.relpath(os.path.join(root, file), os.path.join(path, '..'))
            if selected_subdirs == None or relpath.split(os.path.sep)[1] in selected_subdirs:
                ziph.write(os.path.join(root, file), relpath)
    ziph.close()
    return zip_name


