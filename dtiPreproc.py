#!/Users/admin/anaconda/bin/python

import textwrap
import dicom
import re
import os
import shutil
import sys
import argparse


def getDTIdirectory(directory):
    '''
    Input : subject directory location
    Output : DTIdirectories
    '''
    DTIdirectories = []
    for root, dirs, files in os.walk(directory):

        #Looping through the bunch of files
        for directory in dirs:

            if re.search('DTI_72D',directory,flags=re.IGNORECASE):
                DTIdirectories.append(os.path.abspath(directory))

    return DTIdirectories

def dicomConversion(outputDir,DTIdirectories):
    # Make output directory
    try:
        os.mkdir(outputDir)
    except:
        pass

    # Dicom conversion
    if len(os.listdir(outputDir)) == 0: # if empty
        print '\tDicom Conversion'
        print '\t--------------------------------'
        for DTIdirectory in DTIdirectories:
            command = '/ccnc_bin/mricron/dcm2nii -o {outputDir} \
                        {DTIdirectory}'.format(
                                            outputDir=outputDir,
                                            DTIdirectory=DTIdirectory)
            dcm2niiConversionOutput = os.popen(command).read()

def nameChange(outputDir):
    # Name change
    try:
        initialFiles = os.listdir(outputDir)
        bval = ''.join([x for x in initialFiles if re.search('bval$',x)])
        bvec = ''.join([x for x in initialFiles if re.search('bvec$',x)])
        data = ''.join([x for x in initialFiles if re.search('DTI.*AP.*nii.gz',x)])
        P2A_b0 = ''.join([x for x in initialFiles if re.search('DTI.*PA.*nii.gz',x)])

        shutil.move(os.path.join(outputDir,bval),os.path.join(outputDir,'bvals'))
        shutil.move(os.path.join(outputDir,bvec),os.path.join(outputDir,'bvecs'))
        shutil.move(os.path.join(outputDir,data),os.path.join(outputDir,'data.nii.gz'))
        shutil.move(os.path.join(outputDir,P2A_b0),os.path.join(outputDir,'P2A_b0.nii.gz'))
    except:
        pass
def extractB0images(outputDir,full):
    #Extract B0 images from the data
    print '\tExtract B0 images'
    print '\t--------------------------------'
    if full and len([x for x in os.listdir(outputDir) if x.startswith('A2P_b0_')]) != 9:
        b0Nums = [0,1,10,19,28,37,46,55,64]

        for b0Num in b0Nums:
            command = 'fslroi {outputDir}/data \
                    {outputDir}/A2P_b0_{0} \
                    {0} 1'.format(b0Num,
                    outputDir=outputDir)
            os.popen(command).read()
    elif not full and len([x for x in os.listdir(outputDir) if x.startswith('A2P_b0_')]) != 9:
        b0Nums = [0,1] # Two B0s from A >> P
        for b0Num in b0Nums:
            command = 'fslroi {outputDir}/data \
                    {outputDir}/A2P_b0_{0} \
                    {0} 1'.format(b0Num,
                    outputDir=outputDir)
            os.popen(command).read()

    # Merge B0s
    if not os.path.isfile(os.path.join(
                            outputDir,
                            'b0_images.nii.gz')):
        if full:
            command = 'fslmerge -t {outputDir}/b0_images \
                    {outputDir}/*_b0*'.format(
                                    outputDir=outputDir)
            os.popen(command).read()
        else:
            # Two images of P2A b0
            b0Nums = [0,1] # Two B0s from A >> P
            for b0Num in b0Nums:
                command = 'fslroi {outputDir}/P2A_b0 \
                        {outputDir}/P2A_b0_{0} \
                        {0} 1'.format(b0Num,
                        outputDir=outputDir)
                os.popen(command).read()

            #merge above two mean images
            command = 'fslmerge -t {outputDir}/b0_images \
                    {outputDir}/[PA]2[AP]_b0_[[:digit:]]*.nii.gz'.format(
                                    outputDir=outputDir)
            fslmathsOutput = os.popen(command).read()


def writeAcqParams(outputDir,full):
    '''
    A >> P : 0 -1 0
    A << P : 0 1 0
    4th number : 0.69 ms * 112 * 0.001
    '''

    print '\tWrite Acquisition Parameters'
    print '\t--------------------------------'
    if not os.path.isfile(os.path.join(outputDir,
        'acqparams.txt')):
        # Writing acqparams.txt
        if full:
            acqparams = '''0 -1 0 0.0773
    0 -1 0 0.0773
    0 -1 0 0.0773
    0 -1 0 0.0773
    0 -1 0 0.0773
    0 -1 0 0.0773
    0 -1 0 0.0773
    0 -1 0 0.0773
    0 -1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773'''
        else:
            acqparams = '''0 -1 0 0.0773
    0 -1 0 0.0773
    0 1 0 0.0773
    0 1 0 0.0773'''

        with open(os.path.join(outputDir,
                               'acqparams.txt'),'w') as f:
            f.write(acqparams)

def makeEvenNumB0(outputDir):
    print '\tMake the slice number even'
    print '\t--------------------------------'
    # Make the slice number even
    if not os.path.isfile(os.path.join(outputDir,
        'b0_images_even.nii.gz' )):

        # split B0
        command = 'fslslice {outputDir}/b0_images'.format(outputDir=outputDir)
        fslsliceOutput = os.popen(command).read()

        # merge B0
        slicedImages = [os.path.join(outputDir,x) for x in os.listdir(outputDir) if re.search('slice',x)]

        command = 'fslmerge -z \
                {outputDir}/b0_images_even \
                {slicedImages}'.format(
                outputDir=outputDir,
                slicedImages=' '.join(slicedImages[:-1]))
        fslmergeOutput = os.popen(command).read()

        #Remove splitImages
        for img in slicedImages:
            os.remove(img)

def topup(outputDir):
    print '\tRunning Topup, FSL'
    print '\t--------------------------------'
    if os.path.isfile(os.path.join(
        outputDir,
        'unwarped_images.nii.gz')):
        pass
    else:
        command = 'topup --imain={outputDir}/b0_images_even \
                --datain={outputDir}/acqparams.txt \
                --config=b02b0.cnf \
                --out={outputDir}/topup_results \
                --fout={outputDir}/field \
                --iout={outputDir}/unwarped_images'.format(
                        outputDir=outputDir)

        print os.popen(command).read()


def applytopup(outputDir):
    print '\tApply Topup'
    print '\t--------------------------------'
    if os.path.isfile(os.path.join(
        outputDir,
        'data_topup.nii.gz')):
        pass
    else:
        pwd = os.getcwd()
        os.chdir(outputDir)
        command = 'applytopup \
                --imain=data.nii.gz \
                --datain=acqparams.txt \
                --inindex=1 \
                --topup=topup_results \
                --out=data_topup.nii.gz \
                --method=jac'.format(outputDir=outputDir)
        applyTopUpOutput = os.popen(command).read()
        os.chdir(pwd)

def eddy(outputDir):
    print '\tEddy Correction'
    print '\t--------------------------------'
    # mean of the corrected image
    mean(os.path.join(outputDir,'unwarped_images.nii.gz'),
            os.path.join(outputDir,'unwarped_images_mean'))

    # bet
    os.system('bet {inImg} {output} -m'.format(
        inImg = os.path.join(outputDir,'unwarped_images_mean'),
        output = os.path.join(outputDir,'unwarped_images_mean_brain')))

    # create an index file
    index = ['1']*72
    index = ' '.join(index)

    with open(os.path.join(outputDir,
                           'index.txt'),'w') as f:
        f.write(index)

    #eddy
    command = 'eddy \
            --imain={outputDir}/data_topup.nii.gz \
            --mask={outputDir}/unwarped_images_mean_brain \
            --acqp={outputDir}/acqparams.txt \
            --index={outputDir}/index.txt \
            --bvecs={outputDir}/bvecs \
            --bvals={outputDir}/bvals \
            --topup={outputDir}/my_topup_results \
            --out={outputDir}/eddy_corrected_data'.format(
                    outputDir=outputDir)
    eddyOutput = os.popen(command).read()
    print eddyOutput

def mean(srcImg,trgImg):
    os.system('fslmaths {src} -Tmean {out}'.format(
        src=srcImg,
        out=trgImg))

def dtifit(outputDir):
    print '\tDTIFIT : scalar map calculation'
    print '\t--------------------------------'
    command = 'dtifit \
            -k {outputDir}/data \
            -m {outputDir}/nodif_brain_mask \
            -r {outputDir}/bvecs \
            -b {outputDir}/bvals \
            -o {outputDir}/dti'.format(outputDir=outputDir)
    print os.popen(command).read()



def main(args):

    ################################################
    # InputDir specification
    ################################################
    DTIdirectories = getDTIdirectory(args.directory)

    ################################################
    # outputDir specification
    ################################################
    outputDir = os.path.join(args.directory,'DTIpreproc')

    ################################################
    # Preparation
    ################################################
    dicomConversion(outputDir,DTIdirectories)
    nameChange(outputDir)
    extractB0images(outputDir,args.full)
    writeAcqParams(outputDir,args.full)
    makeEvenNumB0(outputDir)

    ################################################
    # Running topup
    ################################################
    topup(outputDir)

    ################################################
    # applytopup
    ################################################
    applytopup(outputDir)

    ################################################
    # Eddy
    ################################################
    eddy(outputDir)

    ################################################
    # DTIFIT
    ################################################
    if args.dtifit:
        dtifit(outputDir)


if __name__=='__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
            description = textwrap.dedent('''\
                    {codeName} : Pre-process the new diffusion tensor images
                    ==========================================================
                        eg) {codeName}
                        eg) {codeName} --dir /Users/kevin/NOR04_CKI
                        eg) {codeName} --dir /Users/kevin/NOR04_CKI
                    '''.format(codeName=os.path.basename(__file__))))
    parser.add_argument('-dir','--directory',help='Data directory location', default=os.getcwd())
    parser.add_argument('-f','--full',help='Process all B0', default = False)
    parser.add_argument('-d','--dtifit',help='Create FA maps', default = False)
    args = parser.parse_args()
    main(args)
