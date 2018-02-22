import argparse, os, sys, errno, shutil, subprocess

class SafeCopy:

    copyTo = False
    wildcard = False
    sideBySideDiff = False
    preserveMetadata = False

    def __init__(self):
        args = self.parseArguments()

        notCreatedDirs = []
        notCopiedFiles = []
        for src in args['srcPath']:
            if args['r']:
                ncDirs, ncFiles = self.recursiveCopy(src, args['dstPath'])
            else:
                ncDirs, ncFiles = self.singleCopy(src, args['dstPath'])
            notCreatedDirs += ncDirs
            notCopiedFiles += ncFiles
        if len(notCreatedDirs) > 0:
            print("These directories were not copied:")
            self.printConflicts(notCreatedDirs)
        if len(notCopiedFiles) > 0:
            print("\nThese files were not copied:")
            self.printConflicts(notCopiedFiles)
            print("\nAnd here are their diffs:")
            self.printDiffs(notCopiedFiles)

    '''
    Prints the file from the srcPath that conflicted 
        @param conflictList
            a list of lists of the files that conflicted
            essentially ((srcFile, dstFile),)
    '''
    def printConflicts(self, conflictList):
        for conflicts in conflictList:
            print(str(conflicts[0])) 

    def parseArguments(self):
        parser = argparse.ArgumentParser(description="Will copy files if they don't exist in the destination and will diff them if they do exist in the destination.")
        parser.add_argument('srcPath', metavar='srcPath', type=str, help="the path to the file to be copied", nargs="+")
        parser.add_argument('dstPath', metavar='dstPath', type=str, help="the path to copy the files to")
        parser.add_argument('-r', action='store_true', help="use this flag to copy all files in the srcPath")
        parser.add_argument('-y', action='store_true', help="use this flag to get the side by side output for diff")
        parser.add_argument('-p', action='store_true', help="use this flag to copy file metadata when copying the file")
        args = vars(parser.parse_args())
        #print(str(args))
        if args['dstPath'][-1] == '*':
            sys.stderr.write("dstPath has a wildcard and is therefore not understood\n")
            parser.print_help()
        if not os.path.exists(args['dstPath']):
            self.copyTo = True
        if len(args['srcPath']) > 1:
            self.wildcard = True
        if self.wildcard and not os.path.exists(args['dstPath']):
            self.createDirectory(args['dstPath'])
        if args['y']:
            self.sideBySideDiff = True
        if args['p']:
            self.preserveMetadata = True
        return args

    ''' 
    Finds the first occurance of the token in the string, returns -1 if the token is not found
        @param s
            the string to search in for the token
        @param token
            the character to search for in s
        @retval the index that the token was found or -1 if not found
    '''
    def firstOccur(self, s, token):
        for i in range(len(s)):
            if s[i] == token:
                return i
        return -1

    '''
    Determines what the dstPath should be when copying s to dstPath
        @param s
            a file or directory in srcPath
        @param dstPath
            the location to copy the files to
        @retval the location to copy s to
    '''
    def getPathForCopyTo(self, s, dstPath):
        startIndex = self.firstOccur(s, '/')+1
        if startIndex > -1:
            return os.path.join(dstPath+"/", s[startIndex:])
        else:
            return os.path.join(dstPath, s)

    '''
    Creates a directory at the location pathToCreate
        @param pathToCreate 
            the location in the file system to create a directory
    '''
    def createDirectory(self, pathToCreate):
        try:
            os.makedirs(pathToCreate)
        except OSError as e:
            if e.errno == errno.ENOTDIR:
                sys.stderr.write("The directory you tried to copy files into was not a directory. The copy failed.\n")
            elif e.errno != errno.EEXIST:
                raise

    '''
    Copies s to locToCreate and preserves the metadata of s in the copy if requested. This function does not check if the file already exists and will overwrite it if it does exists already. Therefore checking if the file exists is done before this function is called and is only called with parameters that will not result in data loss
        @param s
            the file to copy
        @param locToCreate
            the location to copy s to
    '''
    def copyFile(self, s, locToCreate):
        try:
            if os.path.isdir(s):
                self.createDirectory(locToCreate)
            else:
                shutil.copy(s, locToCreate)
            if self.preserveMetadata:
                shutil.copystat(s, locToCreate)
        except OSError as e:
            sys.stderr.write(str(e) + "\n")

    '''
    Creates the directories in dirsToCopy in dstPath if the directories don't already exist
        @param dirsToCopy
            a directory to copy, or a list of directories to copy
        @param dstPath
            the location to copy to
        @retval a list of pairs of the directories not created
            essentially ((src, dst),)
    '''
    def createDirectories(self, dirsToCopy, dstPath):
        notCreated = []
        if not isinstance(dirsToCopy, list) and not isinstance(dirsToCopy, tuple):
            dirsToCopy = [dirsToCopy]
        for d in dirsToCopy:
            if self.copyTo or self.wildcard:
                pathToCreate = self.getPathForCopyTo(d, dstPath)
            else:
                pathToCreate = os.path.join(dstPath, d)
            if not os.path.exists(pathToCreate):
                self.copyFile(d, pathToCreate)
            else:
                notCreated.append((d,pathToCreate))
        return notCreated

    '''
    Copies all files into the dstPath
        @param srcs a list of paths to files to copy
        @param dstPath the top directory to put the paths of the files into
    '''
    def copyFiles(self, srcs, dstPath):
        notCreated = []
        if not isinstance(srcs, list) and not isinstance(srcs, tuple):
            srcs = [srcs]
        for s in srcs:
            if self.copyTo or self.wildcard:
                locToCreate = self.getPathForCopyTo(s, dstPath)
            else:
                locToCreate = os.path.join(dstPath, s)
            if not os.path.exists(locToCreate):
                self.copyFile(s, locToCreate)
            else:
                notCreated.append((s, locToCreate))
        return notCreated

    '''
    This function will run diff on all of the conflicting files and print the results to stdout
        @param conflicts 
            is a list of tuples
            where the first element of each tuple is the source file that conflicted
            and the second element is the destination file that conflicted
    '''
    def printDiffs(self, conflicts):
        printedADiff = False
        for c in conflicts:
            args = ['diff', c[0], c[1]]
            if self.sideBySideDiff:
                args += ['-y'] 
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, errs = p.communicate()
            if len(out) > 0:
                printedADiff = True
                print("***\ndiff " + str(c[0]) + " " + str(c[1]))
                print(out.decode('utf-8'))
            else:
                print("There was no difference between " + str(c[0]) + " and " + str(c[1]))
        if printedADiff:
            print("***")
       
    '''
    This function will find every file in the srcPath and copy it over to the dstPath if it does not conflict.
        @param srcPath 
            the path to a directory or file to copy.
            If this argument is a file, it calls singleCopy(2) on that file
        @param dstPath
            the location to copy the files in srcPath to
        @retval (notCreatedDirs, notCopiedFiles)
            notCreatedDirs is a list of the directories that were not created
            notCopiedFiles is the list of files not copied
    '''
    def recursiveCopy(self, srcPath, dstPath):
        if not os.path.isdir(srcPath):
            return self.singleCopy(srcPath, dstPath)
        if srcPath[-1] != '/':
            srcPath += '/'
        if self.copyTo:
            dirsToCopy = []
        else:
            dirsToCopy = [srcPath]
        filesToCopy = []
        for dirPath, dirNames, fileNames in os.walk(srcPath):
            for d in dirNames:
                dirsToCopy.append(os.path.join(dirPath, d))
            for f in fileNames:
                filesToCopy.append(os.path.join(dirPath, f))
        notCreatedDirs = self.createDirectories(dirsToCopy, dstPath)
        notCopiedFiles = self.copyFiles(filesToCopy, dstPath)
        return notCreatedDirs, notCopiedFiles

    '''
    This function will copy srcPath to dstPath the way cp would unless srcPath is a directory. In that case it will make the directory dstPath and will copy the metadata of srcPath if the -p flag was given
        @param srcPath
            the path to a directory or file to copy
        @param dstPath
            the location to copy the files to
        @retval (notCreatedDirs, notCopiedFiles)
            notCreatedDirs is a list of the directories that were not created
            notCopiedFiles is the list of files not copied
    '''
    def singleCopy(self, srcPath, dstPath):
        if os.path.isdir(srcPath):
            print("Only copying directory, but not its contents. To copy contents, use the -r flag.")
            if os.path.exists(dstPath):
                return self.createDirectories(srcPath, dstPath), ()
            else:
                self.copyFile(srcPath, dstPath)
        else:
            if os.path.exists(dstPath):
                return (), self.copyFiles(srcPath, dstPath)
            else:
                self.copyFile(srcPath, dstPath)
        return (), ()

if __name__ == "__main__":
    SafeCopy()
