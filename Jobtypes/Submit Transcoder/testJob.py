#!/usr/bin/python


import os
import sys
import logging

if 'QBDIR' in os.environ:
    sys.path.append('%s/api/python' % os.environ['QBDIR'])
elif os.uname()[0] == 'Darwin':
    sys.path.append('/Applications/pfx/qube/api/python')
else:
    sys.path.append('/usr/local/pfx/qube/api/python')

import qb

sys.path.append('../../Modules')
import sequenceTools

class SingleLevelFilter(logging.Filter):
    def __init__(self, passlevel, reject):
        self.passlevel = passlevel
        self.reject = reject

    def filter(self, record):
        if self.reject:
            return (record.levelno != self.passlevel)
        else:
            return (record.levelno == self.passlevel)

'''
Set the root logging settings
'''
rootLogger = logging.getLogger()            

h1 = logging.StreamHandler(sys.stdout)
h1_formatter = logging.Formatter(
        "%(levelname)s: %(message)s")
h1.setFormatter(h1_formatter)
f1 = SingleLevelFilter(logging.INFO, False)
h1.addFilter(f1)
rootLogger.addHandler(h1)

h2 = logging.StreamHandler(sys.stderr)
h2_formatter = logging.Formatter(
        "%(levelname)s:%(name)s:%(funcName)s: %(message)s")
h2.setFormatter(h2_formatter)
f2 = SingleLevelFilter(logging.INFO, True)
h2.addFilter(f2)
rootLogger.addHandler(h2)

rootLogger.setLevel(logging.DEBUG)

'''
Setup this files logging settings
'''
logger = logging.getLogger(__name__)

def chunkWithTolerance(inputList, chunkSize, tolerance):
    '''
    Generate chunks of a list. If the tolerance
    value isn't met, the remaining values are
    added to the last chunk.
    '''
    
    myList = list(inputList) # Make a copy

    logger.debug('Chunk With Tolerance: ' + str(locals()))
    if tolerance > chunkSize:
        tolerance = 0

    resultLists = []
    while len(myList) > 0:
        resultList = []
        count = 0
        while count < chunkSize and len(myList) > 0:
            resultList.append(myList.pop(0))
            count += 1

        if len(resultList) <= tolerance:
            resultLists[-1].extend(resultList)
        else:
            resultLists.append(resultList)

    logger.debug('Chunk with Tolerance Results: ' + str(resultLists))
    logger.debug('Chunk with Tolerance Results Length: ' + str(len(resultLists)))
    return resultLists

def splitPath(inputPath):
    '''
    Split an input path into:
        Folder
        File Name
        File Extension
    '''
    # logger.debug('Splitting Path: ' + str(locals()))
    folder, fullName = os.path.split(inputPath)
    name, extension = os.path.splitext(fullName)

    return folder + '/', name, extension

def setupSequenceJob(qubeJobTemplate, sequenceInitFile, outputFile, preset,
                        selfContained=True, frameRange='ALL', audioFile='',
                        smartUpdate=True, fillMissingFrames=True, transcoderFolder='',
                        segmentDuration=200, maxSegmentsPerOutput=20, maxSegmentTolerance=5):
    '''
    Setup a qube job dictionary based on the input.
    Required Inputs:
        qubeJobTemplate (dictionary)
            Template qube job dictionary to build from.
        sequenceInitFile (string)
            One image from the input image sequence.
            Can be any image from the sequence.
        outputFile (string)
            The destination file for the output
            of the transcoder.
        preset (string)
            The blender file that serves as the template
            for the transcoding process.
    Optional:
        selfContained (boolean)
            Determines if the outputFile should be a
            reference quicktime movie or self-contained.
            Self-contained movies are much larger and take
            more time to create.  Referenced quicktimes
            are much smaller, and much faster to create.
            However, referenced quicktimes must maintain
            their connectiong their associated inputs.
        frameRange (string)
            The output frame range to render from the input
            image sequence. Ex: 1-10
        audioFile (string)
            The audio file to be added to the output file.
            This audio should match the exact timeline of
            the input image sequence.
        smartUpdate (boolean)
            Automatically update only the segments and outputs
            that have been changed since the last transcode.
        transcoderFolder (string)
            The folder in which to store all files related
            to the transcoding process.  This includes the
            segmented movies and the blender projects. If
            creating a referenced output file, these are
            the segments that movie will reference.
        fillMissingFrames (boolean)
            Automatically fill in missing frames with the
            last frame that exists.  This is useful for
            creating quicktimes from sequences rendered on
            every nth frame.
    Advanced:
        segmentDuration (integer)
            Frame count for each segment.
        maxSegmentsPerOutput (integer)
            Maximum number of segments that can be in each
            output file.  If the number of segments needed
            for the sequence exceeds this amount, the output
            file is split into multiple segments of this
            length.
        maxSegmentTolerance (integer)
            If the maxSegmentsPerOutput limit is reached,
            check that the input sequence exceeds this tolerance
            value as well. If not, keep the outputFile as one file.

    Agenda
        The agenda is setup in 3 main sections:
            Initialization:
                Purpose
                    This single subjobs loads the input sequence
                    into the provided blender scene preset.
                    This is done once, then all subsequent
                    jobs reference the resulting scene file.
                Package
                    None
                resultPackage
                    None
                Naming
                    Initialize
            Segments:
                Purpose
                    These subjobs each create their assigned
                    segment of the image sequence.
                Package
                    frameRange (string)
                        Range of frames to render for this segment.
                    segmentFile (string)
                        Destination path for the segment file.
                resultPackage
                    changes (boolean)
                        Returns if any changes were made for
                        this segment.
                    segmentFile (string)
                        Destination path for the segment file
                        that actually rendered.  Sometimes file
                        issues occur where the output file can't
                        be overwritten, so we automatically
                        compensate for this.
                Naming
                    Segment: (frameRange)
            Final Outputs:
                Purpose
                    These subjobs render the output files.
                    They are split up based on the number of segments
                    and the max segments per output.  They are placed
                    in the agenda right after their dependent segments
                    have been processed.
                Package
                    segmentSubjobs (list of strings)
                        List of the names of the dependant
                        segment subjobs.
                    outputFile (string)
                        destination for the output
                resultPackage
                    outputPaths (string)
                        Path to the final output file.
                Naming
                    Output: (outputFile)

    Callbacks
        Callbacks are added to unblock subjobs when they are
        ready to be processed.
            Initialization subjob completion
                Once the initialization is complete, all
                segment subjobs are unblocked.
            Segment subjobs complete.
                Once all segments that pertain to a final
                output are complete, that output subjob
                is unblocked.
            Job retried
                If the job is retried





    '''

    ''' ---- Pre-Processing For Agenda ---- '''

    logger.debug('Setup Sequence: ' + str(locals()))

    ''' General '''
    mySequence = sequenceTools.Sequence(sequenceInitFile, frameRange)
    sequenceName = mySequence.getName()
    if not transcoderFolder:
        transcoderFolder = os.path.join(os.path.dirname(outputFile), '_Transcoder/')

    ''' Initialize '''
    init = qb.Work()
    init['name'] = 'Initialize'


    ''' Segments

    Use the qube chunk method to split up the frame range.
    Then prep each segment:
        Add the frameRange to the package.
        Add the segmentFile to the package.
        Change the subjob name to Segment: (frameRange)
        Submit as blocked, because they will be unblocked
            once the initialize command is completed.
    '''
    segments = qb.genchunks(segmentDuration, '1-' + str(mySequence.getDuration()))
    for segment in segments:
        segment['package']= {}
        segment['package']['frameRange'] = segment['name']

        outputFolder, outputName, outputExtension = splitPath(outputFile)
        segmentFile = os.path.join(transcoderFolder, 'Segments/')
        segmentFile += outputName + '/'
        segmentFile += "Segment" + segment['name'].split('-')[0] + outputExtension
        segment['package']['segmentFile'] = segmentFile

        segment['status'] = 'blocked'
        segment['name'] = 'Segment:' + segment['name']


    ''' Final Outputs '''
    finalOutputSegments = chunkWithTolerance(segments, maxSegmentsPerOutput, maxSegmentTolerance)

    finalOutputs = []
    count = 1
    for outputSegment in finalOutputSegments:
        output = qb.Work()
        output['package'] = {}

        segmentSubjobs = []
        for segment in outputSegment:
            segmentSubjobs.append(segment['name'])
        output['package']['segmentSubjobs'] = segmentSubjobs

        outputFolder, outputName, outputExtension = splitPath(outputFile)
        finalOutputFile = outputFolder + outputName
        if len(finalOutputSegments) > 1:
            finalOutputFile += '_' + chr(64+count)
        finalOutputFile += outputExtension
        output['package']['outputFile'] = finalOutputFile

        output['status'] = 'blocked'
        output['name'] = 'Output: ' + os.path.basename(finalOutputFile)

        count += 1

        finalOutputs.append(output)


    '''
    Callbacks
        1 - Unblock the segments when the initialize command is completed.
        2 - Unblock the outputs when the dependant segments are completed.
    '''

    callbacks = []
    
    ''' Unblock Segments '''
    callback = {}
    callback['triggers'] = 'complete-work-self-Initialize'
    callback['language'] = 'python'
    
    code = 'import qb\n'
    for segment in segments:
        code += '%s%s%s' % ('\nqb.workunblock(\'%s:', segment['name'], '\' % qb.jobid())')
    code += '\nqb.unblock(qb.jobid())'
    callback['code'] = code
    
    callbacks.append(callback)
    
    ''' Unblock Outputs '''
    for finalOutput in finalOutputs:
        callback = {}
        triggers = []

        for segment in finalOutput['package']['segmentSubjobs']:
            triggers.append('complete-work-self-' + segment)
        callback['triggers'] = ' and '.join(triggers)
        callback['language'] = 'python'

        code = 'import qb\n'
        code += '%s%s%s' % ('\nqb.workunblock(\'%s:', finalOutput['name'], '\' % qb.jobid())')
        code += '\nqb.unblock(qb.jobid())'
        callback['code'] = code

        callbacks.append(callback)

    ''' ---- Now put the job together ---- '''

    job = qubeJobTemplate

    ''' General '''
    job['name'] = 'Quicktime: ' + sequenceName
    job['prototype'] = 'Submit Transcoder'

    ''' Package '''
    job['package'] = {}
    job['package']['sequence'] = sequenceInitFile
    job['package']['audioFile'] = audioFile
    job['package']['outputFile'] = outputFile
    job['package']['preset'] = preset
    job['package']['selfContained'] = selfContained
    job['package']['smartUpdate'] = smartUpdate
    job['package']['fillMissingFrames'] = fillMissingFrames
    job['package']['frameRange'] = '1-' + str(mySequence.getDuration())
    job['package']['transcoderFolder'] = transcoderFolder

    ''' Agenda '''
    job['agenda'] = []
    job['agenda'].append(init)
    job['agenda'].extend(segments)

    ''' Place the final outputs after their last segment. '''
    for outputNum, output in enumerate(finalOutputs):
        lastSegmentName = output['package']['segmentSubjobs'][-1]
        lastSegmentIndex = None
        for index, segment in enumerate(segments):
            if segment['name'] == lastSegmentName:
                lastSegmentIndex = index
                break
        if lastSegmentIndex != None:
            job['agenda'].insert(lastSegmentIndex+2+outputNum, output) # +2 for Initialization and last segment
        else:
            logger.error("ERROR: Unable to find last segment for output " + output['name'])

    ''' Callbacks '''
    if not job.get('callbacks', None):
        job['callbacks'] = []
    job['callbacks'].extend(callbacks)

    return job


def testMoreSegments():
    # Set basic job properties
    job = {}
    job['cpus'] = 50
    job['requirements'] = ''
    job['reservations'] = 'host.processors=1'
    job['flagsstring'] = 'auto_wrangling'
    # job['hosts'] = 'bchapman.local'
    job['priority'] = 100
    job['hostorder'] = '+host.processors.avail'
    sequenceFile = '/Volumes/theGrill/Elevate_NonSeries_Projects/ElevateAtHome_Leadership/Renders/_Proxies/testIS/IS/LeadershipWeb_00000.tga'
    outputFile = '/Volumes/theGrill/Elevate_NonSeries_Projects/ElevateAtHome_Leadership/Renders/_Proxies/testIS/LeadershipWeb_MoreSegments.mov'
    preset = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets/1280x720-29.97-ProRes4444.blend'
    audioFile = '/Volumes/theGrill/Elevate_NonSeries_Projects/ElevateAtHome_Leadership/Renders/_Proxies/testIS/LeadershipWeb.wav'
    job = setupSequenceJob(job, sequenceFile, outputFile, preset, audioFile=audioFile, maxSegmentsPerOutput=5,
        fillMissingFrames=True, maxSegmentTolerance=2, segmentDuration=200)
    logger.info(job)
    qb.submit([job])
    # qb.archivejob('job.qja', job)

def testLessSegments():
    # Set basic job properties
    job = {}
    job['cpus'] = 50
    job['requirements'] = ''
    job['reservations'] = 'host.processors=1'
    job['flagsstring'] = 'auto_wrangling'
    # job['hosts'] = 'bchapman.local'
    job['priority'] = 100
    job['hostorder'] = '+host.processors.avail'
    sequenceFile = '/Volumes/theGrill/Elevate_NonSeries_Projects/ElevateAtHome_Leadership/Renders/_Proxies/testIS/IS/LeadershipWeb_00000.tga'
    outputFile = '/Volumes/theGrill/Elevate_NonSeries_Projects/ElevateAtHome_Leadership/Renders/_Proxies/testIS/LeadershipWeb_LessSegments.mov'
    preset = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets/1280x720-29.97-ProRes4444.blend'
    audioFile = '/Volumes/theGrill/Elevate_NonSeries_Projects/ElevateAtHome_Leadership/Renders/_Proxies/testIS/LeadershipWeb.wav'
    job = setupSequenceJob(job, sequenceFile, outputFile, preset, audioFile=audioFile, maxSegmentsPerOutput=1,
        fillMissingFrames=True, maxSegmentTolerance=0, segmentDuration=1000)
    logger.info(job)
    qb.submit([job])

def testBibleStory():
    # Set basic job properties
    job = {}
    job['cpus'] = 50
    job['requirements'] = ''
    job['reservations'] = 'host.processors=1'
    job['flagsstring'] = 'auto_wrangling'
    # job['hosts'] = 'bchapman.local'
    job['priority'] = 100
    job['hostorder'] = '+host.processors.avail'
    sequenceFile = '/Volumes/theGrill/Elevate_Series/Port_Of_Call/Kids/Art_Anim/_Renders_and_Exports/Image_Sequences/L2/POC_BS_L2_00000.png'
    outputFile = '/Volumes/theGrill/Staff-Directories/Brennan/Testing/Transcoder/POC_BS_L2_Test.mov'
    preset = '/Volumes/theGrill/.qube/Jobtypes/Submit Transcoder/Presets/720p_wAlpha.blend'
    audioFile = '/Volumes/theGrill/Staff-Directories/Brennan/Testing/Transcoder/POC_BS_L2.wav'
    job = setupSequenceJob(job, sequenceFile, outputFile, preset, audioFile=audioFile, maxSegmentsPerOutput=5,
        fillMissingFrames=True, maxSegmentTolerance=2, segmentDuration=200)
    logger.info(job)
    qb.submit([job])

# testMoreSegments()
# testLessSegments()
testBibleStory()