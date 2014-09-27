
from enum import Enum
import hashlib
from os import path, listdir, mkdir, walk
import zipfile
import json
import time
import shutil


class ModPack:
    mods = []
    libraries = []
    args = None
    mcversion = None
    name = None
    configzip = None
    tweaks = []

    def format_for_mcupdate_plus(self):
        entry = {"mcversion": self.mcversion}
        if self.configzip:
            entry["config"] = {"file": self.configzip, "version": int(time.time())}
        if self.mods:
            entry["mods"] = []
            for mod in self.mods:
                entry["mods"].append(mod.format_for_mcupdater_plus())
        if self.libraries:
            entry["libraries"] = []
            for lib in self.libraries:
                entry["libraries"].append(lib.format_for_mcupdater_plus())
        if self.args:
            entry["additionalArguments"] = self.args
        if self.tweaks:
            entry["tweakClasses"] = []
            for tweak in self.tweaks:
                entry["tweakClasses"].append(tweak)
        return entry


class LibInfo:
    group = None
    name = None
    version = None
    url = None
    classifier = None

    def format_for_mcupdater_plus(self):
        entry = {"group": self.group, "name": self.name, "version": self.version}
        if self.url:
            entry["url"] = self.url
        if self.classifier:
            entry["classifier"] = self.classifier
        return entry

    @staticmethod
    def from_maven_line(mavenline):
        args = mavenline.split(":",4)
        lib = LibInfo()
        lib.group = args[0]
        lib.name = args[1]
        lib.version = args[2]
        if len(args) > 3:
            if not args[3] == "":
                lib.classifier = args[3]
        if len(args) > 4:
            lib.url = args[4]
        return lib


class ModInfo:
    forClient = False
    forServer = False
    sha1Sum = ""
    md5Sum = ""
    filename = ""
    filepath = ""
    name = None
    modid = None
    authors = None
    version = None
    revision = None
    mcversion = None
    type = None

    def load_from_fml(self, filename):
        print("Processing FML Mod: {}".format(filename))
        if not path.exists(filename):
            raise FileNotFoundError("The provided JAR did not exist for FML import.")
        self.filename = path.basename(filename)
        self.sha1Sum = sha1_of_file(filename)
        self.md5Sum = md5_of_file(filename)
        self.type = ModType.fml
        if not zipfile.is_zipfile(filename):
            raise RuntimeError("The file specified was not a valid archive!")
        thearchive = zipfile.ZipFile(filename)
        if not "mcmod.info" in thearchive.namelist():
            print("The mod {} does not contain a mcmod.info...".format(path.basename(filename)))
            self.name = path.basename(filename)
            self.authors = "unknown"
            self.version = "unknown"
            self.modid = path.basename(filename)
        else:
            mcmodinfo = thearchive.open("mcmod.info")
            mcmodjson = json.loads(mcmodinfo.read().decode())
            if "modlist" in mcmodjson:
                mcmodjson = mcmodjson["modlist"]
            if type(mcmodjson) == list:
                mcmodjson = mcmodjson[0]
            self.name = mcmodjson["name"]
            self.version = mcmodjson["version"] if "version" in mcmodjson else "unknown"
            self.modid = mcmodjson["modid"]
            self.authors = str(mcmodjson["authors"]) if "authors" in mcmodjson else "unknown"
        thearchive.close()
        del thearchive

    def format_for_mcupdater_plus(self):
        entry = {}
        if self.modid:
            entry["modid"] = self.modid
        if self.version:
            entry["version"] = self.version
        if self.revision:
            entry["revision"] = self.revision
        entry["file"] = '{}/{}'.format(self.filepath, self.filename) if self.filepath else self.filename
        if self.type == ModType.classpath:
            entry["type"] = "jar"
        elif self.type == ModType.fml:
            entry["type"] = "forge"
        elif self.type == ModType.litemod:
            entry["type"] = "liteloader"
        entry["md5"] = self.md5Sum
        if self.forClient and not self.forServer:
            entry["side"] = "client"
        elif self.forServer and not self.forClient:
            entry["side"] = "server"
        return entry


class ModType(Enum):
    classpath = 1
    fml = 2
    litemod = 3


def sha1_of_file(filename):
    file = open(filename, 'rb')
    sha = hashlib.sha1()
    while True:
        chunk = file.read(2**10)
        if not chunk:
            break
        sha.update(chunk)
    file.close()
    del file
    return sha.hexdigest()


def md5_of_file(filename):
    file = open(filename, 'rb')
    md = hashlib.md5()
    while True:
        chunk = file.read(2**10)
        if not chunk:
            break
        md.update(chunk)
    file.close()
    del file
    return md.hexdigest()


def main():
    print("Jamcraft MCUpdater Pack Builder")
    if path.exists("output"):
        shutil.rmtree("output")

    mkdir("output")
    mkdir(path.join("output", "modpack"))
    mkdir(path.join(path.join("output", "modpack"), "latest"))

    modpack = ModPack()

    if path.exists(path.join("input", "mods-fml")):
        for file in listdir(path.join("input", "mods-fml")):
            mod = ModInfo()
            mod.load_from_fml(path.join(path.join("input", "mods-fml"), file))
            modpack.mods.append(mod)
    modpack.mcversion = "1.6.4"

    if path.exists(path.join("input","libraries.txt")):
        libfile = open(path.join("input","libraries.txt"))
        for libline in libfile:
                print("Addling library: {}".format(libline.strip()))
                modpack.libraries.append(LibInfo.from_maven_line(libline.strip()))
        libfile.close()
        del libfile

    if path.exists(path.join("input","tweaks.txt")):
        tweaksfile = open(path.join("input","tweaks.txt"))
        for tweaksline in tweaksfile:
            print("Activating Tweak: {}".format(tweaksline.strip()))
            modpack.tweaks.append(tweaksline.strip())
        tweaksfile.close()
        del tweaksfile

    if path.exists(path.join("input","config")):
        modpack.configzip = "config.zip"
        configzip = zipfile.ZipFile(path.join("output", "modpack", "latest", "config.zip"), "w")
        for dirpath, dnames, fnames in walk(path.join("input", "config")):
            for fname in fnames:
                print("Adding Config File: {}".format(path.relpath(path.join(dirpath, fname), "input")))
                configzip.write(path.join(dirpath, fname), path.relpath(path.join(dirpath, fname), "input"))
        configzip.close()
        del configzip

    packjson = open(path.join(path.join("output", "modpack"), path.join("latest", "pack.json")), "w")
    json.dump(modpack.format_for_mcupdate_plus(), packjson, sort_keys=True, indent=4)
    packjson.close()

main()
