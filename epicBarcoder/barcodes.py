#!/usr/bin/env python

import pandas as pd

#Within each sample, group by barcode; assign each barcode a list of zOTUs
#for each read that contains that barcode (i.e. list can contain redundancies)
#INPUT:  Fasta file with droplet barcode and zOTU information in the header
#OUTPUT: A dictionary where each sampID maps to a dictionary of droplet 
#	 barcodes:[zOTU1, zOTU1, zOTU2, ...]
def createBarcodeDict(inFileName):
    inFile = open(inFileName, 'r')
    barcodeSamples = {}
    for line in inFile:
        if '>' in line:
            line = line.strip().split(';')
            samp = line[0].split('_')[0].replace('>','')
            bc = line[0].split('droplet_bc=')[1]
            otu = line[1]
            if samp not in barcodeSamples:
                barcodeSamples[samp] = {bc:[otu]}
            else:
                if bc not in barcodeSamples[samp]:
                    barcodeSamples[samp][bc] = [otu]
                else:
                    barcodeSamples[samp][bc].append(otu)
    inFile.close()
    return barcodeSamples

#Summarize the richness of the barcoding data from different samples into a
#log file
#INPUT:  barcodeDict generated by createBarcodeDict
#	 list of sampleIDs in desired order
#OUTPUT: path to output log file, a tab-delimited summary of barcode patterns
#	     for each input sample
def summarizeBarcoding(barcodeDict, sampIDs, outFileName):
    outFile = open(outFileName, 'w')
    outFile.write('#sample\ttotal_barcodes\tsingletons\treplicates\tmultiplets\n')
    for s in sampIDs:
        if s not in barcodeDict:
            continue
        outList = [s]
        outList.append(str(len(barcodeDict[s])))
        singletons = 0
        replicates = 0
        multiplets = 0
        for bc in barcodeDict[s]:
            if len(barcodeDict[s][bc]) == 1:
                singletons += 1
            elif(len(set(barcodeDict[s][bc])) == 1):
                replicates += 1
            elif(len(set(barcodeDict[s][bc])) > 1):
                multiplets += 1
        outList = outList + map(str, [singletons, replicates, multiplets])
        outFile.write('\t'.join(outList) + '\n')
    outFile.close()

#Take in a dictionary of zOTU:taxonomy, then construct a dataframe that
#groups zOTUs by those that share taxonomy (i.e. tOTUs)
#INPUT:  taxonomic dictionary, output of importSintax()
#OUTPUT: pandas dataframe with zOTU indexes, and two columns with unique tOTU
#        ID and full taxonomic string
def tOTUmap(taxDict):
    index = []
    tax_tOTU = {}
    data = []
    i = 1
    for zOTU in taxDict:
        index.append(zOTU)
        tax = taxDict[zOTU]
        if tax not in tax_tOTU:
            tOTU = 'tOtu' + str(i)
            tax_tOTU[tax] = tOTU
            taxList = [tOTU, tax]
            i += 1
        else:
            taxList = [tax_tOTU[tax], tax]
        data.append(taxList)
    columns = ['tOTU', 'taxonomy']
    otuDf = pd.DataFrame(data, index=index, columns=columns)
    return otuDf

#Calculate abundances of background OTUs based on singleton barcodes
#Background OTUs defined as unique taxonomic classifications
#INPUT:  barcode dictionary (output of createBarcodeDict)
#        taxonomic dictionary (output of importSintax with 'final' setting)
#OUTPUT: relative abundance pandas dataframe, with sample IDs in the columns and
#        tOTUs as row indexes
def tOTU_singletonAbundances(barcodeDict, taxDict):
    otuDf = tOTUmap(taxDict)
    abundances = {}
    totals = {}
    for s in barcodeDict:
        total = 0
        backgroundOTU = {}
        for bc in barcodeDict[s]:
            #If there is one unique barcode with only one sequence mapped to it
            #(true barcode singleton)
            if len(barcodeDict[s][bc]) == 1:
                zOTU = barcodeDict[s][bc][0]
                tOTU = otuDf['tOTU'][zOTU]
                if tOTU not in backgroundOTU:
                    backgroundOTU[tOTU] = 1
                else:
                    backgroundOTU[tOTU] += 1
                total += 1
        abundances[s] = backgroundOTU
        totals[s] = total
    #Convert abundance counts to relative abundances
    relAbundances = {}
    for s in abundances:
        relAbund = {}
        for otu in abundances[s]:
            relAbund[otu] = float(abundances[s][otu]) / totals[s]
        relAbundances[s] = relAbund
    relDf = pd.DataFrame.from_dict(relAbundances)
    return relDf
