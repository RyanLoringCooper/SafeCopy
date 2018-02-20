import argparse, os, sys, errno, shutil, subprocess

copyTo = False
wildcard = False

def parseArguments():
    #TODO need to use narg on srcPath
    parser = argparse.ArgumentParser(description="Will copy files if they don't exist in the destination and will diff them if they do exist in the destination.")
    parser.add_argument('srcPath', metavar='srcPath', type=str, help="the path to the file to be copied")
    parser.add_argument('dstPath', metavar='dstPath', type=str, help="the path to copy the files to")
    parser.add_argument('-r', action='store_true', help="use this flag to copy all files in the srcPath")
    args = vars(parser.parse_args())
    print(str(args))
    if args['dstPath'][-1] == '*':
        sys.stderr.write("dstPath has a wildcard and is therefore not understood\n")
        parser.print_help()
    return args

def firstOccur(s, token):
    for i in range(len(s)):
        if s[i] == token:
            return i
    return -1

def getPathForCopyTo(s, dstPath):
    startIndex = firstOccur(s, '/')+1
    if startIndex > -1:
        return os.path.join(dstPath+"/", s[startIndex:])
    else:
        return os.path.join(dstPath, s)

def createDirectory(pathToCreate):
    try:
        os.makedirs(pathToCreate)
    except OSError as e:
        if e.errno == errno.ENOTDIR:
            sys.stderr.write("The directory you tried to copy files into was not a directory. The copy failed.\n")
        elif e.errno != errno.EEXIST:
            raise

def createDirectories(dirsToCopy, dstPath):
    notCreated = []
    if not isinstance(dirsToCopy, list) and not isinstance(dirsToCopy, tuple):
        dirsToCopy = [dirsToCopy]
    for d in dirsToCopy:
        if copyTo:
            pathToCreate = getPathForCopyTo(d, dstPath)
        else:
            pathToCreate = os.path.join(dstPath, d)
        if not os.path.exists(pathToCreate):
            createDirectory(pathToCreate)
        else:
            notCreated.append((d,pathToCreate))
    return notCreated

def copyFile(s, locToCreate):
    try:
        shutil.copy2(s, locToCreate)
    except OSError as e:
        sys.stderr.write(str(e) + "\n")

'''
Copies all files into the dstPath
    @param srcs a list of paths to files to copy
    @param dstPath the top directory to put the paths of the files into
'''
def copyFiles(srcs, dstPath):
    notCreated = []
    if not isinstance(srcs, list) and not isinstance(srcs, tuple):
        srcs = [srcs]
    for s in srcs:
        if copyTo:
            locToCreate = getPathForCopyTo(s, dstPath)
        else:
            locToCreate = os.path.join(dstPath, s)
        if not os.path.exists(locToCreate):
            copyFile(s, locToCreate)
        else:
            notCreated.append((s, locToCreate))
    return notCreated

'''
This function will run diff on all of the conflicting files and print the results to stdout
    @param conflicts is a list of tuples
        where the first element of each tuple is the source file that conflicted
        and the second element is the destination file that conflicted
'''
def getDiffs(conflicts):
    for c in conflicts:
        p = subprocess.Popen(['diff', c[0], c[1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, errs = p.communicate()
        if len(out) > 0:
            print("***\ndiff " + str(c[0]) + " " + str(c[1]))
            print(str(out))
        else:
            print("There was no difference between " + str(c[0]) + " and " + str(c[1]))
    print("***")
   
def recursiveCopy(srcPath, dstPath):
    if not os.path.isdir(srcPath):
        singleCopy(srcPath, dstPath)
    if srcPath[-1] != '/':
        srcPath += '/'
    if copyTo:
        dirsToCopy = []
    else:
        dirsToCopy = [srcPath]
    filesToCopy = []
    for dirPath, dirNames, fileNames in os.walk(srcPath):
        for d in dirNames:
            if wildcard:
                dToCopy = os.path.join(dirPath[len(srcPath):], d)
            else:
                dToCopy = os.path.join(dirPath, d)
            dirsToCopy.append(dToCopy)
        for f in fileNames:
            if wildcard:
                fToCopy = os.path.join(dirPath[len(srcPath):], f)
            else:
                fToCopy = os.path.join(dirPath, f)
            filesToCopy.append(fToCopy)
    notCreatedDirs = createDirectories(dirsToCopy, dstPath)
    notCreatedFiles = copyFiles(filesToCopy, dstPath)
    if(len(notCreatedFiles) > 0):
        print("These things were not copied")
        print(notCreatedDirs)
        print(notCreatedFiles)
        getDiffs(notCreatedFiles)

def singleCopy(srcPath, dstPath):
    if os.path.isdir(srcPath):
        print("Only copying directory, but not its contents. To copy contents, use the -r flag.")
        if os.path.exists(dstPath):
            createDirectories(srcPath, dstPath)
        else:
            createDirectory(dstPath)
    else:
        if os.path.exists(dstPath):
            copyFiles(srcPath, dstPath)
        else:
            copyFile(srcPath, dstPath)

if __name__ == "__main__":
    args = parseArguments()
    if not os.path.exists(args['dstPath']):
        copyTo = True
    if args['srcPath'][-1] == '*':
        args['srcPath'] = args['srcPath'][:-1]
        wildcard = True
    if args['r']:
        recursiveCopy(args['srcPath'], args['dstPath'])
    else:
        singleCopy(args['srcPath'], args['dstPath'])
