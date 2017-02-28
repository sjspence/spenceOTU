import os
import subprocess
from collections import defaultdict
import epride as ep


def getExtension(fileName):
    fileName = fileName.split('.')
    fileExt = '.' + fileName[len(fileName)-1]
    return fileExt


def clusterWithUsearch(usearchPath, inFile, percIdentity):
    env = os.environ
    percIdentity = str(percIdentity)
    extension = getExtension(inFile)
    outFile = inFile.replace(extension, '_' + percIdentity + '.fa')
    clustFile = inFile.replace(extension, '_' + percIdentity + '.uc')
    subprocess.call([usearchPath, "-cluster_fast", inFile,
                     "-sort", "length", "-id", percIdentity,
                     "-centroids", outFile, "-uc",
                     clustFile], env=env)


def move_barcodes_and_type_to_fasta_id(bc_seq, bridge_dict):
    bridge_dict = {key: ep.expand_primers(ep.reverse_complement(val))
                   for key, val in bridge_dict.items()}
    for seq_id, seq in bc_seq:
        for bridge_id, bridges in bridge_dict.items():
            for bridge in bridges:
                if bridge in seq:
                    bc, rest = seq.split(bridge)
                    if len(bc) == 20:
                        seq_id = "{} barcode={} sequence_type={}".format(seq_id.strip(),
                                                                         bc, bridge_id)
                        yield([seq_id, rest])


def process_barcode_info(input_seq_file, output_seq_file, bridge_dict):
    seqs = ep.read_fasta(input_seq_file)
    fasta_iter = move_barcodes_and_type_to_fasta_id(seqs, bridge_dict)
    ep.write_fasta(fasta_iter, output_seq_file)


def get_len_distr(seqs):
    len_distr_dict = defaultdict(list)
    for seq_id, seq in seqs:
        seq_type_id = seq_id.split("_")[-1]
        len_distr_dict[seq_type_id].append(int(len(seq) / 10) * 10)
    return len_distr_dict


def get_seed_dict(uc_file):
    seed_dict = {}
    with open(uc_file) as f:
        for line in f:
            if line.split("\t")[0] == "H":
                seq_id = line.split("\t")[8].split()[0]
                seed_id = line.split("\t")[9].split()[0]
                seed_dict[seq_id] = seed_id
            if line.split("\t")[0] == "S":
                seq_id = line.split("\t")[8].split()[0]
                seed_dict[seq_id] = seq_id
    return seed_dict


def add_otus_to_fasta(seq_file, uc_file, output_file):
    seeds = get_seed_dict(uc_file)
    seq_acc = []
    for seq_id, seq in ep.read_fasta(seq_file):
        short_id = seq_id[1:].split()[0]
        seed_id = seeds[short_id]
        new_seq_id = "{} OTU={}".format(seq_id.strip(), seed_id)
        seq_acc.append([new_seq_id, seq])
    ep.write_fasta(seq_acc, output_file)


def process_mapping_file(mapping_file):
    sampIDs = []
    mapping = {}
    readCounts = {}
    with open(mapping_file, 'r') as inFile:
        for line in inFile:
            if '#' not in line:
                line = line.strip().split('\t')
                mapping[line[1]] = line[0].replace('_', 's')
                readCounts[line[1]] = 0
                sampIDs.append(line[0].replace('_', 's'))
    return [sampIDs, mapping, readCounts]

def process_fastq_and_mapping_file(input_file, output_file, mapping_file, quality_summary_file):
    sampIDs, mapping, readCounts = process_mapping_file(mapping_file)
    with open(input_file, 'r') as inFile:
        with open(output_file, 'w') as outFile:
            i = 0
            j = 0
            nextSeq = False
            for line in inFile:
                if nextSeq:
                    outFile.write(line)
                    nextSeq = False
                if i % 4 == 0:
                    for bc in mapping:
                        if bc in line:
                            readCounts[bc] += 1
                            newLine = line.strip().replace('@', '>' + mapping[bc] + '_' + str(j) + ' ')
                            newLine = newLine + ' orig_bc=' + bc + ' new_bc=' + bc + ' bc_diffs=0\n'
                            outFile.write(newLine)
                            nextSeq = True
                            j += 1
                i += 1
    total = 0
    with open(quality_summary_file, 'w') as summaryFile:
        for s in sampIDs:
            for bc in mapping:
                if mapping[bc] == s:
                    summaryFile.write(s + '\t' + str(readCounts[bc]) + '\n')
                    total += readCounts[bc]
        summaryFile.write('Total\t' + str(total))
