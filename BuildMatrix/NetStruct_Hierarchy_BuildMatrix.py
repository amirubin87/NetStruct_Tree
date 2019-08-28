__author__ = 't-amirub'
'''
This script generates a matrix of distances for a selected window of random entries.

It should be used in parallel, on different windows indexes.
See the "Matrix joiner" section in the end for merging these matrixes.

Parameters are:
inputFile outputFolder windowSize windowIndex shuffeledFile totalSnps totalIndividuals
parmas:
    inputFile - path to file with genetics data - in each line i all of the individuals alleles at loci i. The format is - space seperating each locus, comma seperating the alleles
    outputFolder - path to folder in which we write outputs
    totalSnps - the number of snps in the inputFile
    totalIndividuals - the number of individuals in the inputFile
    allelesString - comma seperated symbols. Each symbol in the string is a symbol of an allele in the input data
    alleleMissingValueChar - the character representing a missing value


    *** Non mandatory parameters *** 
    binaryMode - if true, input is 0,1 or 2. 0 is mapped to 00, 1 is mapped to 10, and 2 is mapped to 11.
    pivoted - if true each line represents a loci. Alleles in this loci of all individuals are listed in each line.
          If false, each line represents an individual.

    *** For parallel execution ***
    windowSize - size of window to be processed.
    windowIndex - index of the window to be processes - will be read from the shuffeledFile.
    shuffeledFile - a path to a file generated by buildShuffledArray(n) where n is the number of snps in the inputFile.

Sample executions:
Run on small dummy (ACTG) input
    python ./NetStruct_Hierarchy_BuildMatrix.py ./SampleInputGenes.txt ./sample/ 3 4 A,B,C,D,T,G N

Run on small dummy (binary, pivoted) input
    python ./NetStruct_Hierarchy_BuildMatrix.py ./SampleInputGenesBinary.txt ./sample/ 4 3 notUsed NotUsed True True

Run on a small Arabidopsis data with 20 individuals and 10k snps in a binary format, pivoted
    python ./NetStruct_Hierarchy_BuildMatrix.py ./Sample_Arabidopsis_20_ind_10k_snps.tsv ./Sample_Arabidopsis/ 10000 20 notUsed NotUsed True True
Referring to the last run, you can execute NetStruct_Hierarchy_v1 on the output:
Cd to parent dir, where the jar is located and run
    java -jar NetStruct_Hierarchy_v1.jar -pro ./BuildMatrix/Sample_Arabidopsis/ -pm ./BuildMatrix/Sample_Arabidopsis/Distances/Matrix10000_0.csv -pmn ./BuildMatrix/Sample_Arabidopsis/ind2SampleSite.txt -pss ./BuildMatrix/Sample_Arabidopsis/SampleSites.txt -minb 9 -mino 9 -ss 0.001
Take a look at the output files
    .\BuildMatrix\Sample_Arabidopsis\Weighted_true_Dynamic_false_minSize_9_StepSize_0.001_Beta_1.0\

'''
import sys
import os
import csv
import datetime
from random import shuffle
import random


#********************************************************************
#********************************************************************
#********************************************************************
#
#                        Utills
#
#********************************************************************
#********************************************************************
#********************************************************************

#********************************************************************
# Builds a shuffled array of length n, writes it to output
#********************************************************************
def buildShuffledArray(n, output):
    x = [i for i in range(n)]
    shuffle(x)
    with open(output, "w") as f:
        for i in x:
            f.write(str(i)+',')

#********************************************************************
# Generates all missing dirs in the path.
# BEWARE of race conditions!!
#********************************************************************
def makeDirs(pathToFile):
    pathToDir = os.path.dirname(pathToFile)
    if not os.path.exists(pathToDir):
        os.makedirs(pathToDir)

#********************************************************************
# Writing msg to logPath
#********************************************************************
def writeToLog(msg, logPath):
    logMsg = 'log ' + str(datetime.datetime.now()) +': ' + msg
    print(logMsg)

    with open(logPath, "a") as f:
        f.write(logMsg)
        f.write('\n')

#********************************************************************
#********************************************************************
#********************************************************************
#
#                       Data handlers
#
#********************************************************************
#********************************************************************
#********************************************************************

def writeDistancesToFile(distances, totalCount, output):
    numOfIndividuals = len(distances.keys())
    makeDirs(output)
    with open(output, "w") as f:
        for i in range(0, numOfIndividuals-1):
            for j in range(i+1, numOfIndividuals):
                f.write(str(float(distances.get(i).get(j))/totalCount)+',')
            f.write('\n')

def writeCountsToFile(defaultAmount,counts,countsPath):
    makeDirs(countsPath)
    with open(countsPath, "w") as f:
        f.write('DefaultAmountOfSnps ' + str(defaultAmount) + '\n')
        f.write('If there are missing values, they will be listed below in the following format: \n')
        f.write('<index of first individual>,<index of second individual>,<# of valid snps>\n')
        for i in counts.keys():
            for j in counts.get(i).keys():
                f.write(str(i)+','+str(j)+','+str(counts.get(i).get(j))+'\n')

def writeFrequenciesPerLocusToFile(frequenciesPerLocus, frequenciesPerLocusPath):
    numOfLoci = len(frequenciesPerLocus.items())
    makeDirs(frequenciesPerLocusPath)
    with open(frequenciesPerLocusPath, "w") as f:
        wrCsv = csv.writer(f, lineterminator='\n')
        for l in range(0, numOfLoci):
            #except list.
            wrCsv.writerow(frequenciesPerLocus.get(l))

def readFrequenciesPerLocusFile(frequenciesPerLocusPath):
    frequenciesPerLocus = dict()
    with open(frequenciesPerLocusPath) as f:
        lis=[line.replace('\n','').split(',') for line in f]    # create a list of lists
        for i,x in enumerate(lis):
            y = []
            for c in x:
                y.append(int(c))
            frequenciesPerLocus[i] = y
    return frequenciesPerLocus

#********************************************************************
# Sum the non missing entries at locus l
#********************************************************************
def nonMissingEntiresAtLocus(frequenciesPerLocus, l):
    ans = 0
    # the lsat entry is the amount of missing ones
    for i in range(len(frequenciesPerLocus[l])-1):
        ans += frequenciesPerLocus[l][i]
    return ans

#********************************************************************
# reads the RANDOM window in size @windowSize in index @windowIndex from the @genesFile, based on the @randomIndexListFile
# The data in the @randomIndexListFile should be the output of buildShuffledArray(TotalSnps).
# To run on a single machine use @windowSize=TotalSnps and @windowIndex=0.
#********************************************************************
def readRandomWindow(inputFile, windowSize, windowIndex, shuffeledFile, totalSnps, totalIndividuals, allelesString, alleleMissingValueChar, binaryMode, pivoted):
    startIndex = windowSize*windowIndex
    endIndex = windowSize*(windowIndex+1)
    if startIndex >= totalSnps :
        return None
    if endIndex > totalSnps:
        endIndex = totalSnps
    if(shuffeledFile!=""):
        randomListFile = open(shuffeledFile,'r')
        randomList = randomListFile.readline().split(',')
    else:
        # We use all the snps
        randomList = range(totalSnps)
    # We take the (random) alleles from the random list
    allelesToUse = randomList[startIndex:endIndex]
    allelesToUse = [int(x) for x in allelesToUse]

    window = dict()
    for indi in range(0,totalIndividuals):
        window[indi] = dict()

    if pivoted:
        return ExtractWindowPivoted(allelesToUse, inputFile, totalIndividuals, window, allelesString, alleleMissingValueChar, binaryMode)
    else:
        return ExtractWindow(allelesToUse, inputFile, totalIndividuals, window, allelesString, alleleMissingValueChar, binaryMode)

#********************************************************************
# Extracting the window when the input schema is: in each line i we have all of the alleles of individual i.
#********************************************************************
def ExtractWindowPivoted(allelsToUse, inputFile, totalIndividuals, window, allelesString, alleleMissingValueChar,binaryMode):
    alleleSymbols = allelesString.split(',')
    fp = open(inputFile, 'r')
    lociCounter = 0
    for i, line in enumerate(fp):
        if i in allelsToUse:
            parts = line.split()
            for indi in range(0, totalIndividuals):
                if binaryMode:  
                        if parts[indi]=='1':
                            val1=1
                            val2=0
                        elif parts[indi]=='2':
                            val1=1
                            val2=1
                        elif parts[indi]=='0':
                            val1=0
                            val2=0
                        else:
                            val1=-1
                            val2=-1
                else:
                    alleles = parts[indi].split(',')
                    # missing value                
                    if (alleles[0] == alleleMissingValueChar) or (alleles[1] == alleleMissingValueChar):
                        val1 = -1
                        val2 = -1
                    else:
                        val1 = alleleSymbols.index(alleles[0])
                        val2 = alleleSymbols.index(alleles[1])
                window[indi][lociCounter] = [val1, val2]
            lociCounter = lociCounter + 1
    fp.close()
    return window
    
#********************************************************************
# Extracting the window when the input schema is: in each line i we have all of the individuals alleles at loci i.
#********************************************************************
def ExtractWindow(allelsToUse, inputFile, totalIndividuals, window, allelesString, alleleMissingValueChar,binaryMode):    
    alleleSymbols = allelesString.split(',')    
    fp = open(inputFile, 'r')
    line_counter=0
    for indi, line in enumerate(fp):
        line_counter+=1
        if len(line)>2:
            loci = line.split()
            for l in range(len(loci)):                
                if l in allelsToUse:
                    if binaryMode:  
                        if loci[l]=='1':
                            val1=1
                            val2=0
                        elif loci[l]=='2':
                            val1=1
                            val2=1
                        elif loci[l]=='0':
                            val1=0
                            val2=0
                        elif loci[l]=='-':
                            val1=-1
                            val2=-1
                        else:
                            error_msg = 'ERROR - you are running in binary mode, and there is a value which isnt one of 0,1,2,-. Perhaps you forgat to set binaryMode to False?.\n At line ' + str(line_counter) + ', column ' +str(l) +', value is ' + loci[l]
                            raise ValueError(error_msg)
                    else:
                        alleles = loci[l].split(',')
                        # missing value
                        if (alleles[0] == alleleMissingValueChar) or (alleles[1] == alleleMissingValueChar):                            
                            val1 = -1
                            val2 = -1
                        else:
                            val1 = alleleSymbols.index(alleles[0])
                            val2 = alleleSymbols.index(alleles[1])
                    window[indi][l] = [val1, val2]                
    fp.close()
    return window

#********************************************************************
#********************************************************************
#********************************************************************
#
#                Distance and frequencies calculations
#
#********************************************************************
#********************************************************************
#********************************************************************

#********************************************************************
# For each locus in the given @window, we calc the frequencies of each allele.
#********************************************************************
def calcFrequenciesPerLocus(window, logFile, allelesString):
    # +1 for the missing value option
    numOfAlleles = len(allelesString.split(','))+1
    numOfSnpsInWindow= len(window.get(0).keys())
    frequenciesPerLocus = dict()
    for locus in range(0,numOfSnpsInWindow):
        if locus%max(1,int(numOfSnpsInWindow/100)) ==0:
            writeToLog('calcFrequenciesPerLocus finished ' + str(locus) + ' out of ' + str(numOfSnpsInWindow), logFile)
        counts = [0]*numOfAlleles
        for i,val in window.items():
            snp = val[locus]
            # if any of the allele is -1, we wont count this SNP
            if(snp[0]==-1) or (snp[1] == -1):
                counts[numOfAlleles-1] = counts[numOfAlleles-1] + 2
            else:
                indexToIncrement = snp[0]
                counts[indexToIncrement] = counts[indexToIncrement] + 1
                indexToIncrement = snp[1]
                counts[indexToIncrement] = counts[indexToIncrement] + 1
        frequenciesPerLocus[locus] = counts
    return frequenciesPerLocus

#********************************************************************
# Calculates the distance between two individuals based on the given @frequenciesPerLocus
#********************************************************************
def calcDistancesBetweenTwo(i, j, frequenciesPerLocus):
    dist = 0
    valid=0
    for l in i.keys():
        a = i.get(l)[0]
        b = i.get(l)[1]
        c = j.get(l)[0]
        d = j.get(l)[1]
        # we only use cases where all of the alleles are not '-1'
        if ( a!=-1 and b!=-1 and c!=-1 and d!=-1):
            valid = valid +1
            Iac = 1 if(a==c) else 0
            Iad = 1 if(a==d) else 0
            Ibc = 1 if(b==c) else 0
            Ibd = 1 if(b==d) else 0
            # guard rail - we wont divide by 0
            nonMissingEntires = max(1, nonMissingEntiresAtLocus(frequenciesPerLocus,l))
            f_a = float(frequenciesPerLocus[l][a])/nonMissingEntires
            f_b = float(frequenciesPerLocus[l][b])/nonMissingEntires
            dist = dist+ 0.25*((1-f_a)*(Iac+Iad) +(1-f_b)*(Ibc+Ibd))
    return (dist,valid)

#********************************************************************
# Calcs the distance between any two individuals in the given @window based on the given @frequenciesPerLocus
#********************************************************************
def calcDistances(window, frequenciesPerLocus, logFile):
    allDist = dict()
    allValids = dict()
    numOfIndividuals = len(window.keys())
    numOfSnpsInWindow= (len(list(window.values())[0].keys()))
    for i in window.keys():
        if i%max(1,int(numOfIndividuals/100))==0:
            writeToLog('calcDistances finished ' + str(i) + ' out of ' + str(numOfIndividuals), logFile)
        allDist[i] = dict()
        for j in window.keys():
            if (i<j):
                S_ij,C_ij = calcDistancesBetweenTwo(window.get(i),window.get(j),frequenciesPerLocus)
                allDist[i][j] = S_ij
                if C_ij<numOfSnpsInWindow:
                    if allValids.get(i) is None:
                        allValids[i] = dict()
                    allValids[i][j] = C_ij
    return allDist,allValids

#********************************************************************
#********************************************************************
#********************************************************************
#
#                          Main
#
#********************************************************************
#********************************************************************
#********************************************************************

def main(inputVector):
    if len(inputVector)<6:
        print ("Required parameters: inputFile outputFolder totalSnps totalIndividuals binaryMode.")
        print ("If binaryMode is false, additional required parameters: allelesString alleleMissingValueChar.")        
        print ("Non mandatory parameters: pivoted windowSize windowIndex shuffeledFile.")
        return
    # parse command line options

    inputFile = inputVector[1]
    outputFolder = inputVector[2]
    totalSnps = int(inputVector[3])
    totalIndividuals = int(inputVector[4])
    
    if inputVector[5]=='True':
        binaryMode = True
    elif inputVector[5]=='False':
        binaryMode = False
    else:
        raise ValueError('binaryMode must be "True" or "False"')

    if binaryMode:
        allelesString='0,1,2'
        alleleMissingValueChar='-'
    else:
        if len(inputVector)<=7:
            raise 'When binaryMode is false, you must supply allelesString and alleleMissingValueChar'
        else:
            allelesString = inputVector[6] #"A,T,C,G"
            alleleMissingValueChar = inputVector[7] #'N'

    pivoted= False
    if len(inputVector)>8:
        pivoted = bool(inputVector[8])

    # for parallel execution
    shuffeledFile = ""
    windowSize = totalSnps
    windowIndex = 0
    if len(inputVector)>9:
        windowSize = int(inputVector[9])
    if len(inputVector)>10:
        windowIndex = int(inputVector[10])
    if len(inputVector)>11:
        shuffeledFile = inputVector[11]


    '''# can be used for adhoc runs
    inputFile = "./SampleInputGenes.txt"
    outputFolder = "./sample/"
    windowSize = 3
    windowIndex = 0
    shuffeledFile = ""
    totalSnps = 3
    totalIndividuals = 4
    binaryMode = False
    # each character in the string is a symbol of an allele in the input data
    allelesString = 'A,C,T,G,XYZ'
    # a single character to represent a missing value
    alleleMissingValueChar = 'N'
    pivoted = False'''
    

    #First check that the output file doesnt exist.
    distancesPath = outputFolder + "Distances/Matrix" + str(windowSize) + "_" + str(windowIndex) + ".csv"
    countsPath = outputFolder + "Distances/Counts" + str(windowSize) + "_" + str(windowIndex) + ".csv"
    logFile = outputFolder + "Log/" + str(windowSize) + "_" + str(windowIndex) + ".log"
    makeDirs(logFile)

    if os.path.isfile(distancesPath):
        # file exists
        writeToLog("file exist, exit.", logFile)
        return
    window =readRandomWindow(inputFile, windowSize, windowIndex, shuffeledFile, totalSnps, totalIndividuals, allelesString, alleleMissingValueChar, binaryMode, pivoted)

    # Step A - frequencies per locus.
    # For DR reasons - we check if the file exists.
    frequenciesPerLocusPath = outputFolder + "Frequencies/" + str(windowSize) + "_" + str(windowIndex) + ".csv"

    if os.path.isfile(frequenciesPerLocusPath):
        # file exists
        frequenciesPerLocus = readFrequenciesPerLocusFile(frequenciesPerLocusPath)
    else:
        frequenciesPerLocus = calcFrequenciesPerLocus(window, logFile, allelesString)

        writeFrequenciesPerLocusToFile(frequenciesPerLocus,frequenciesPerLocusPath)

    # Step B - distances between individuals
    distances,counts = calcDistances(window,frequenciesPerLocus, logFile)

    # this version does not support the option to divided each distance by the amount of valid snps.
    # in case you have many invalid entires in your data, it may influence the result.
    writeDistancesToFile(distances,len(list(window.values())[0].keys()),distancesPath)
    writeCountsToFile(len(list(window.values())[0].keys()),counts,countsPath)

if __name__ == "__main__":
    main(sys.argv)

#********************************************************************
#********************************************************************
#********************************************************************
#
#                          Matrix joiner
#
#********************************************************************
#********************************************************************
#********************************************************************

#********************************************************************
# Initialize a matrix of distances for n individuals
#********************************************************************
def initMatrix(n):
    m = dict()
    for i in range(0,n):
        m[i]=dict()
        for j in range(i+1,n):
            m[i][j]=0
    return m

#********************************************************************
# Merges random @numOfWindowsToGroup.
# @DistancesFolder should hold all distances as writen by writeDistancesToFile
# Normally @firstIndexOfWindows=0 and @lastIndexOfWindows=(int)totalSnps/windowSize
#********************************************************************
def mergeMatrixsRandomly(outputPath,distancesFolder,windowSize,numOfWindowsToGroup,firstIndexOfWindows,lastIndexOfWindows,numOfIndividuals):
    m = initMatrix(numOfIndividuals)
    totalCount =0
    for iw in random.sample(range(firstIndexOfWindows, lastIndexOfWindows), numOfWindowsToGroup):
        count = int(open(distancesFolder + "Counts" + str(windowSize) +"_"+ str(iw) +".csv").readline().split()[1])
        totalCount = totalCount + count
        fname = distancesFolder +"Matrix"+ str(windowSize) +"_"+ str(iw) +".csv"
        with open(fname) as fp:
            for i, line in enumerate(fp):
                if(len(line)>1):
                    parts = line.replace(",\n","").split(',')
                    for j in range(0,len(parts)):
                        d = (float(parts[j]))
                        oldD = m[i][(i+1)+j]
                        # the first entry in each line is the distance between i and i+1
                        m[i][(i+1)+j] =  oldD + d
    writeDistancesToFile(m, totalCount, outputPath)

