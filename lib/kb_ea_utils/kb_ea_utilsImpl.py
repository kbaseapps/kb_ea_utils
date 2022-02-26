# -*- coding: utf-8 -*-
#BEGIN_HEADER
import sys
import traceback
from biokbase.workspace.client import Workspace as workspaceService
import requests
requests.packages.urllib3.disable_warnings()
import subprocess
import os
import re
from datetime import datetime
from pprint import pprint, pformat
import uuid
import numpy as np

from ReadsUtils.ReadsUtilsClient import ReadsUtils as ReadsUtils
from SetAPI.SetAPIServiceClient import SetAPI
from KBaseReport.KBaseReportClient import KBaseReport
#END_HEADER


class kb_ea_utils:
    '''
    Module Name:
    kb_ea_utils

    Module Description:
    Utilities for Reads Processing
    '''

    ######## WARNING FOR GEVENT USERS ####### noqa
    # Since asynchronous IO can lead to methods - even the same method -
    # interrupting each other, you must be *very* careful when using global
    # state. A method could easily clobber the state set by another while
    # the latter method is running.
    ######################################### noqa

    VERSION = ""
    GIT_URL = ""
    GIT_COMMIT_HASH = ""

    #BEGIN_CLASS_HEADER
    FASTQ_STATS     = "/usr/local/bin/fastq-stats"
    FASTQ_MULTX     = "/usr/local/bin/fastq-multx"
    #FASTQ_JOIN      = "/usr/local/bin/fastq-join"
    FASTQ_JOIN      = "/kb/module/bin/fastq-join"
    DETERMINE_PHRED = "/usr/local/bin/determine-phred"


    def log(self, target, message):
        if target is not None:
            target.append(message)
        print(message)
        sys.stdout.flush()

    def get_reads_ref_from_params(self, params):
        if 'read_library_ref' in params:
            return params['read_library_ref']

        if 'workspace_name' not in params and 'read_library_name' not in params:
            raise ValueError('Either "read_library_ref" or "workspace_name" with ' +
                             '"read_library_name" fields are required.')

        return str(params['workspace_name']) + '/' + str(params['read_library_name'])


    def get_report_string (self, fastq_file):
        cmd = ("fastq-stats", fastq_file)
        cmd_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        outputlines = []
        while True:
            line = cmd_process.stdout.readline()
            outputlines.append(line)
            if not line: break
            #self.log(console, line.replace('\n', ''))
        
        cmd_process.stdout.close()
        retcode = cmd_process.wait()
        self.log(None, 'return code: ' + str(retcode) + '\n')
        if retcode != 0:
            # not sure how to test this
            self.log(None, "".join(outputlines))
            raise ValueError('Error running fastq_stats, return code: {}'.format(recode))
        report = '====' + fastq_file + '====' + "\n"
        report += "".join(outputlines)
        return report


    def get_ea_utils_result (self,refid, input_params):
      ref = [refid]
      DownloadReadsParams={'read_libraries':ref}
      dfUtil = ReadsUtils(self.callbackURL)
      x=dfUtil.download_reads(DownloadReadsParams)
      report = ''
      fwd_file = None
      rev_file = None

      fwd_file    =  x['files'][ref[0]]['files']['fwd']
      otype =  x['files'][ref[0]]['files']['otype']

      #case of interleaved
      if (otype == 'interleaved'):
          report += self.get_report_string (fwd_file)

      #case of separate pair
      if (otype == 'paired'):
         report += self.get_report_string (fwd_file)

         rev_file    =  x['files'][ref[0]]['files']['rev']
         report += self.get_report_string (rev_file)

      #case of single end
      if (otype == 'single'):
         report += self.get_report_string (fwd_file)
      #print report
      return report

    #END_CLASS_HEADER

    # config contains contents of config file in a hash or None if it couldn't
    # be found
    def __init__(self, config):
        #BEGIN_CONSTRUCTOR
        self.workspaceURL = config['workspace-url']
        self.shockURL = config['shock-url']
        self.scratch = os.path.abspath(config['scratch'])
        self.data = os.path.abspath(config['data'])
        self.handleURL = config['handle-service-url']
        self.serviceWizardURL = config['service-wizard-url']

        self.callbackURL = os.environ.get('SDK_CALLBACK_URL')
        if self.callbackURL == None:
            raise ValueError ("SDK_CALLBACK_URL not set in environment")

        if not os.path.exists(self.scratch):
            os.makedirs(self.scratch)
        if not os.path.exists(self.data):
            os.makedirs(self.data)
        #END_CONSTRUCTOR
        pass


    def get_fastq_ea_utils_stats(self, ctx, input_params):
        """
        This function should be used for getting statistics on read library object types
        The results are returned as a string.
        :param input_params: instance of type
           "get_fastq_ea_utils_stats_params" (if read_library_ref is set,
           then workspace_name and read_library_name are ignored) ->
           structure: parameter "workspace_name" of String, parameter
           "read_library_name" of String, parameter "read_library_ref" of
           String
        :returns: instance of String
        """
        # ctx is the context object
        # return variables are: ea_utils_stats
        #BEGIN get_fastq_ea_utils_stats
        token = ctx['token']
        wsClient = workspaceService(self.workspaceURL)
        # add additional info to provenance here, in this case the input data object reference
        input_reads_ref = self.get_reads_ref_from_params(input_params)

        ea_utils_stats = ''
        ea_utils_stats = self.get_ea_utils_result(input_reads_ref, input_params)

        #END get_fastq_ea_utils_stats

        # At some point might do deeper type checking...
        if not isinstance(ea_utils_stats, basestring):
            raise ValueError('Method get_fastq_ea_utils_stats return value ' +
                             'ea_utils_stats is not type basestring as required.')
        # return the results
        return [ea_utils_stats]

    def run_app_fastq_ea_utils_stats(self, ctx, input_params):
        """
        This function should be used for getting statistics on read library object type.
        The results are returned as a report type object.
        :param input_params: instance of type
           "run_app_fastq_ea_utils_stats_params" (if read_library_ref is set,
           then workspace_name and read_library_name are ignored) ->
           structure: parameter "workspace_name" of String, parameter
           "read_library_name" of String, parameter "read_library_ref" of
           String
        :returns: instance of type "Report" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: report
        #BEGIN run_app_fastq_ea_utils_stats
        print (input_params)

        wsClient = workspaceService(self.workspaceURL)
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        # add additional info to provenance here, in this case the input data object reference
        input_reads_ref = self.get_reads_ref_from_params(input_params)
        if 'workspace_name' not in input_params:
            raise ValueError('"workspace_name" field is required to run this App"')
        workspace_name = input_params['workspace_name']
        provenance[0]['input_ws_objects'] = [input_reads_ref]

        #ref=['11665/5/2', '11665/10/7', '11665/11/1' ]
        #ref=['11802/9/1']
        report = self.get_ea_utils_result(input_reads_ref, input_params)
        reportObj = {
            'objects_created':[],
            'text_message':report
        }

        reportName = 'run_fastq_stats_'+str(uuid.uuid4())
        report_info = wsClient.save_objects({
            'workspace':workspace_name,
            'objects':[
                 {
                  'type':'KBaseReport.Report',
                  'data':reportObj,
                  'name':reportName,
                  'meta':{},
                  'hidden':1, # important!  make sure the report is hidden
                  'provenance':provenance
                 }
            ] })[0]
        print('saved Report: '+pformat(report_info))

        report = { "report_name" : reportName,"report_ref" : str(report_info[6]) + '/' + str(report_info[0]) + '/' + str(report_info[4]) }

        #print (report)
        #END run_app_fastq_ea_utils_stats

        # At some point might do deeper type checking...
        if not isinstance(report, dict):
            raise ValueError('Method run_app_fastq_ea_utils_stats return value ' +
                             'report is not type dict as required.')
        # return the results
        return [report]

    def get_ea_utils_stats(self, ctx, input_params):
        """
        This function should be used for getting statistics on fastq files. Input is string of file path.
        Output is a report string.
        :param input_params: instance of type "ea_utils_params"
           (read_library_path : absolute path of fastq files) -> structure:
           parameter "read_library_path" of String
        :returns: instance of String
        """
        # ctx is the context object
        # return variables are: report
        #BEGIN get_ea_utils_stats
        read_library_path = input_params['read_library_path']
        report = self.get_report_string (read_library_path)
        #END get_ea_utils_stats

        # At some point might do deeper type checking...
        if not isinstance(report, basestring):
            raise ValueError('Method get_ea_utils_stats return value ' +
                             'report is not type basestring as required.')
        # return the results
        return [report]

    def calculate_fastq_stats(self, ctx, input_params):
        """
        This function should be used for getting statistics on fastq files. Input is string of file path.
        Output is a data structure with different fields.
        :param input_params: instance of type "ea_utils_params"
           (read_library_path : absolute path of fastq files) -> structure:
           parameter "read_library_path" of String
        :returns: instance of type "ea_report" (read_count - the number of
           reads in the this dataset total_bases - the total number of bases
           for all the the reads in this library. gc_content - the GC content
           of the reads. read_length_mean - The average read length size
           read_length_stdev - The standard deviation read lengths phred_type
           - The scale of phred scores number_of_duplicates - The number of
           reads that are duplicates qual_min - min quality scores qual_max -
           max quality scores qual_mean - mean quality scores qual_stdev -
           stdev of quality scores base_percentages - The per base percentage
           breakdown) -> structure: parameter "read_count" of Long, parameter
           "total_bases" of Long, parameter "gc_content" of Double, parameter
           "read_length_mean" of Double, parameter "read_length_stdev" of
           Double, parameter "phred_type" of String, parameter
           "number_of_duplicates" of Long, parameter "qual_min" of Double,
           parameter "qual_max" of Double, parameter "qual_mean" of Double,
           parameter "qual_stdev" of Double, parameter "base_percentages" of
           mapping from String to Double
        """
        # ctx is the context object
        # return variables are: ea_stats
        #BEGIN calculate_fastq_stats
        read_library_path = input_params['read_library_path']
        ea_report = self.get_report_string (read_library_path)
        print('ea_report')
        print(ea_report)
        ea_stats = {}
        report_lines = ea_report.splitlines()
        report_to_object_mappings = {'reads': 'read_count',
                                     'total bases': 'total_bases',
                                     'len mean': 'read_length_mean',
                                     'len stdev': 'read_length_stdev',
                                     'phred': 'phred_type',
                                     'dups': 'number_of_duplicates',
                                     'qual min': 'qual_min',
                                     'qual max': 'qual_max',
                                     'qual mean': 'qual_mean',
                                     'qual stdev': 'qual_stdev'}
        integer_fields = ['read_count', 'total_bases', 'number_of_duplicates']
        for line in report_lines:
            line_elements = line.split()
            line_value = line_elements.pop()
            line_key = " ".join(line_elements)
            line_key = line_key.strip()
            if line_key in report_to_object_mappings:
                # print ":{}: = :{}:".format(report_to_object_mappings[line_key],line_value)
                value_to_use = None
                if line_key == 'phred':
                    value_to_use = line_value.strip()
                elif report_to_object_mappings[line_key] in integer_fields:
                    value_to_use = int(line_value.strip())
                else:
                    value_to_use = np.nan_to_num(float(line_value.strip()))
                ea_stats[report_to_object_mappings[line_key]] = value_to_use
            elif line_key.startswith("%") and not line_key.startswith("%dup"):
                if 'base_percentages' not in ea_stats:
                    ea_stats['base_percentages'] = dict()
                dict_key = line_key.strip("%")
                ea_stats['base_percentages'][dict_key] = np.nan_to_num(float(line_value.strip()))
        # populate the GC content (as a value betwwen 0 and 1)
        if 'base_percentages' in ea_stats:
            gc_content = 0
            if "G" in ea_stats['base_percentages']:
                gc_content += ea_stats['base_percentages']["G"]
            if "C" in ea_stats['base_percentages']:
                gc_content += ea_stats['base_percentages']["C"]
            ea_stats["gc_content"] = gc_content / 100
        # set number of dups if no dups, but read_count
        if 'read_count' in ea_stats and 'number_of_duplicates' not in ea_stats:
            ea_stats["number_of_duplicates"] = 0

        print('ea_stats')
        print(ea_stats)
        #END calculate_fastq_stats

        # At some point might do deeper type checking...
        if not isinstance(ea_stats, dict):
            raise ValueError('Method calculate_fastq_stats return value ' +
                             'ea_stats is not type dict as required.')
        # return the results
        return [ea_stats]

    def run_Fastq_Multx(self, ctx, params):
        """
        :param params: instance of type "run_Fastq_Multx_Input"
           (run_Fastq_Multx() ** ** demultiplex read libraries to readsSet)
           -> structure: parameter "workspace_name" of type "workspace_name"
           (** Common types), parameter "index_info" of type "textarea_str",
           parameter "desc" of String, parameter "index_mode" of String,
           parameter "input_reads_ref" of type "data_obj_ref", parameter
           "input_index_ref" of type "data_obj_ref", parameter
           "output_reads_name" of type "data_obj_name", parameter
           "barcode_options" of type "Barcode_Options" (Parameter groups) ->
           structure: parameter "use_header_barcode" of type "bool",
           parameter "trim_barcode" of type "bool", parameter
           "suggest_barcodes" of type "bool", parameter "force_edge_options"
           of type "ForceEdge_Options" -> structure: parameter "force_beg" of
           type "bool", parameter "force_end" of type "bool", parameter
           "dist_and_qual_params" of type "DistAndQual_Params" -> structure:
           parameter "mismatch_max" of Long, parameter "edit_dist_min" of
           Long, parameter "barcode_base_qual_score_min" of Long
        :returns: instance of type "run_Fastq_Multx_Output" -> structure:
           parameter "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN run_Fastq_Multx
        console = []
        report = ''
        self.log(console, 'Running run_Fastq_Multx() with parameters: ')
        self.log(console, "\n"+pformat(params))

        token = ctx['token']
        wsClient = workspaceService(self.workspaceURL, token=token)
        headers = {'Authorization': 'OAuth '+token}
        env = os.environ.copy()
        env['KB_AUTH_TOKEN'] = token


        # Instantiate Set API Client and Report API Client
        #SERVICE_VER = 'dev'  # DEBUG
        SERVICE_VER = 'release'
        setAPI_Client = SetAPI (url=self.serviceWizardURL, token=ctx['token'], service_ver=SERVICE_VER)  # dynamic service
        reportAPI_Client = KBaseReport (self.callbackURL, token=ctx['token'], service_ver=SERVICE_VER)  # local method


        # param checks
        required_params = ['workspace_name',
                           'input_reads_ref',
                           'index_mode',
                           'desc',
                           'output_reads_name'
                           ]
        for arg in required_params:
            if arg not in params or params[arg] == None or params[arg] == '':
                raise ValueError ("Must define required param: '"+arg+"'")

        # combined param requirements
        if params['index_mode'] == 'manual':
            if 'index_info' not in params or params['index_info'] == None or params['index_info'] == '':
                raise ValueError ("Must have index_info if index_mode is 'manual'")
        elif params['index_mode'] == 'index-lane':
            if 'input_index_ref' not in params or params['input_index_ref'] == None or params['input_index_ref'] == '':
                raise ValueError ("Must have index lane library if index_mode is 'index-lane'")

        # and param defaults
        defaults = { 'barcode_options': {'use_header_barcode': 0,
                                         'trim_barcode': 1,
                                         'suggest_barcodes': 0
                                        },
                     'force_edge_options': { 'force_beg': 0,
                                             'force_end': 0
                                           },
                     'dist_and_qual_params': { 'mismatch_max': 1,
                                               'edit_dist_min': 2,
                                               'barcode_base_qual_score_min': 1
                                             }
                   }
        for param_group in defaults.keys():
            if param_group not in params or params[param_group] == None:
                params[param_group] = dict()
                for arg in defaults[param_group].keys():
                    params[param_group][arg] = defaults[param_group][arg]
            else:
                for arg in defaults[param_group].keys():
                    if arg not in params[param_group] or params[param_group][arg] == None or params[param_group][arg] == '':
                        params[param_group][arg] = defaults[param_group][arg]


        # Set path to default barcodes
        #
        master_barcodes_path = os.path.join(self.data, "master-barcodes.txt")


        # load provenance
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        provenance[0]['input_ws_objects']=[str(params['input_reads_ref'])]

        # Determine whether read library is of correct type
        #
        try:
            # object_info tuple
            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)

            input_reads_ref = params['input_reads_ref']
            input_reads_obj_info = wsClient.get_object_info_new ({'objects':[{'ref':input_reads_ref}]})[0]
            input_reads_obj_type = input_reads_obj_info[TYPE_I]
            input_reads_obj_type = re.sub ('-[0-9]+\.[0-9]+$', "", input_reads_obj_type)  # remove trailing version
            #input_reads_obj_version = input_reads_obj_info[VERSION_I]  # this is object version, not type version

        except Exception as e:
            raise ValueError('Unable to get read library object info from workspace: (' + str(input_reads_ref) +')' + str(e))

        acceptable_types = ["KBaseFile.PairedEndLibrary", "KBaseFile.SingleEndLibrary"]
        if input_reads_obj_type not in acceptable_types:
            raise ValueError ("Input reads of type: '"+input_reads_obj_type+"'.  Must be one of "+", ".join(acceptable_types))


        if 'input_index_ref' in params and params['input_index_ref'] != None and params['input_index_ref'] != '':
            try:
                # object_info tuple
                [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)

                input_index_ref = params['input_index_ref']
                input_index_obj_info = wsClient.get_object_info_new ({'objects':[{'ref':input_index_ref}]})[0]
                input_index_obj_type = input_index_obj_info[TYPE_I]
                input_index_obj_type = re.sub ('-[0-9]+\.[0-9]+$', "", input_index_obj_type)  # remove trailing version

            except Exception as e:
                raise ValueError('Unable to get index read library object info from workspace: (' + str(input_index_ref) +')' + str(e))

            #acceptable_types = ["KBaseFile.PairedEndLibrary", "KBaseFile.SingleEndLibrary"]
            acceptable_types = ["KBaseFile.SingleEndLibrary"]
            if input_index_obj_type not in acceptable_types:
                raise ValueError ("Input index reads of type: '"+input_index_obj_type+"'.  Must be one of "+", ".join(acceptable_types))
            #if input_index_obj_type != input_reads_obj_type:
            #    raise ValueError ("Input index reads of type: '"+input_index_obj_type+"' must be same as Input reads of type: '"+input_reads_obj_type+"'")


        # Download Reads
        #
        self.log (console, "DOWNLOADING READS")  # DEBUG
        try:
            readsUtils_Client = ReadsUtils (url=self.callbackURL, token=ctx['token'])  # SDK local
        except Exception as e:
            raise ValueError('Unable to get ReadsUtils Client' +"\n" + str(e))
        try:
            if input_reads_obj_type == "KBaseFile.PairedEndLibrary":
                readsLibrary = readsUtils_Client.download_reads ({'read_libraries': [input_reads_ref],
                                                                  'interleaved': 'false'
                                                                  })
            else:
                readsLibrary = readsUtils_Client.download_reads ({'read_libraries': [input_reads_ref]})

        except Exception as e:
            raise ValueError('Unable to download read library sequences from workspace: (' + str(input_reads_ref) +")\n" + str(e))

        input_fwd_file_path = readsLibrary['files'][input_reads_ref]['files']['fwd']
#        input_fwd_path = re.sub ("\.fq$", "", input_fwd_file_path)
#        input_fwd_path = re.sub ("\.FQ$", "", input_fwd_path)
#        input_fwd_path = re.sub ("\.fastq$", "", input_fwd_path)
#        input_fwd_path = re.sub ("\.FASTQ$", "", input_fwd_path)

        if input_reads_obj_type == "KBaseFile.PairedEndLibrary":
            input_rev_file_path = readsLibrary['files'][input_reads_ref]['files']['rev']
#            input_rev_path = re.sub ("\.fq$", "", input_rev_file_path)
#            input_rev_path = re.sub ("\.FQ$", "", input_rev_path)
#            input_rev_path = re.sub ("\.fastq$", "", input_rev_path)
#            input_rev_path = re.sub ("\.FASTQ$", "", input_rev_path)

        sequencing_tech = 'N/A'
        if 'sequencing_tech' in readsLibrary['files'][input_reads_ref]:
            sequencing_tech = readsLibrary['files'][input_reads_ref]['sequencing_tech']


        # don't need phred_type after all
#        phred_type = None
#        if 'phred_type' in readsLibrary['files'][input_reads_ref]:
#            phred_type = readsLibrary['files'][input_reads_ref]['phred_type']
#        else:
#            phred_type = self.exec_Determine_Phred (ctx, {'input_reads_file':input_fwd_file_path})['phred_type']


        # Download index reads (currently must be single end.  why?)
        #
        if 'input_index_ref' in params and params['input_index_ref'] != None and params['input_index_ref'] != '':
            try:
                input_index_ref = params['input_index_ref']
                indexLibrary = readsUtils_Client.download_reads ({'read_libraries': [input_index_ref]#,
                                                                  #'interleaved': 'false'
                                                                  })
            except Exception as e:
                raise ValueError('Unable to download index read library sequences from workspace: (' + str(input_index_ref) +")\n" + str(e))
            input_index_fwd_file_path = indexLibrary['files'][input_index_ref]['files']['fwd']
            #input_index_rev_file_path = indexLibrary['files'][input_index_ref]['files']['rev']


        # Set the output dir
        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()*1000)
        output_dir = os.path.join(self.scratch,'output.'+str(timestamp))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # clean up index_info
        #
        manual_group_id_order = []
        if params['index_mode'] == 'manual':
            index_info_path = None
            if 'index_info' in params and params['index_info'] != None and params['index_info'] != '':

                index_info_buf = []
                for line in params['index_info'].split("\n"):
                    line = line.strip()
                    if line == '':
                        continue
                    row = line.split()
                    if row[0] == "id" or row[0] == "ID" or row[0] == '' or row[0].startswith("#"):
                        continue
                    manual_group_id_order.append(row[0])

                    row_str = "\t".join(row)+"\n"
                    index_info_buf.append(row_str)

                # write index_info
                index_info_path = os.path.join(output_dir, 'index_info.txt')
                index_info_handle = open(index_info_path, 'w', 0)
                index_info_handle.writelines(index_info_buf)
                index_info_handle.close()
            else:
                raise Value ("missing index_info")


        # Prep vars
        #
        multx_cmd = []
        multx_cmd.append(self.FASTQ_MULTX)

        if params['index_mode'] == 'auto-detect':
             multx_cmd.append('-l')
             multx_cmd.append(master_barcodes_path)
        elif params['index_mode'] == 'index-lane':
            multx_cmd.append('-g')
            multx_cmd.append(input_index_fwd_file_path) # what about reverse barcode lane? fastq-multx only accepts single end even for paired end primary reads
        elif params['index_mode'] == 'manual':
            multx_cmd.append('-B')
            multx_cmd.append(index_info_path)
        else:
            raise ValueError ("Bad index_mode: '"+params['index_mode']+"'")


        if 'barcode_options' in params and params['barcode_options'] != None:
            if 'use_header_barcode' in params['barcode_options'] and params['barcode_options']['use_header_barcode'] == 1:
                multx_cmd.append('-H')
            if 'trim_barcode' in params['barcode_options'] and params['barcode_options']['trim_barcode'] == 0:
                multx_cmd.append('-x')
            if 'suggest_barcodes' in params['barcode_options'] and params['barcode_options']['suggest_barcodes'] == 1:
                multx_cmd.append('-n')

        if 'force_edge_options' in params and params['force_edge_options'] != None:
            if 'force_beg' in params['force_edge_options'] and params['force_edge_options']['force_beg'] == 1:
                multx_cmd.append('-b')
            if 'force_end' in params['force_edge_options'] and params['force_edge_options']['force_end'] == 1:
                multx_cmd.append('-e')

        if 'dist_and_qual_params' in params and params['dist_and_qual_params'] != None:
            if 'mismatch_max' in params['dist_and_qual_params'] and params['dist_and_qual_params']['mismatch_max'] != None and params['dist_and_qual_params']['mismatch_max'] != '':
                multx_cmd.append('-m')
                multx_cmd.append(str(params['dist_and_qual_params']['mismatch_max']))
            if 'edit_dist_min' in params['dist_and_qual_params'] and params['dist_and_qual_params']['edit_dist_min'] != None and params['dist_and_qual_params']['edit_dist_min'] != '':
                multx_cmd.append('-d')
                multx_cmd.append(str(params['dist_and_qual_params']['edit_dist_min']))
            if 'barcode_base_qual_score_min' in params['dist_and_qual_params'] and params['dist_and_qual_params']['barcode_base_qual_score_min'] != None and params['dist_and_qual_params']['barcode_base_qual_score_min'] != '':
                multx_cmd.append('-q')
                multx_cmd.append(str(params['dist_and_qual_params']['barcode_base_qual_score_min']))

        # add input files
        multx_cmd.append(input_fwd_file_path)
        if input_reads_obj_type == "KBaseFile.PairedEndLibrary":
            multx_cmd.append(input_rev_file_path)

        # add output files
        out_fwd_base_pattern = output_dir+'/'+'fwd.'
        out_fwd_pattern      = out_fwd_base_pattern+'%.fq'
        multx_cmd.append('-o')
        multx_cmd.append(out_fwd_pattern)
        if input_reads_obj_type == "KBaseFile.PairedEndLibrary":
            out_rev_base_pattern = output_dir+'/'+'rev.'
            out_rev_pattern      = out_rev_base_pattern+'%.fq'
            multx_cmd.append('-o')
            multx_cmd.append(out_rev_pattern)


        # Run
        #
        print(multx_cmd)
        print('running fastq-multx:')
        print('    '+' '.join(multx_cmd))
        try:
            #p = subprocess.Popen(" ".join(multx_cmd), cwd=self.scratch, shell=False)
            #p = subprocess.Popen(" ".join(multx_cmd), cwd=self.scratch, shell=True)
#            p = subprocess.Popen(" ".join(multx_cmd), stdout=subprocess.PIPE, stderr=subprocess.STDERR, cwd=self.scratch, shell=True)
            p = subprocess.Popen(multx_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.scratch)
        except:
            raise ValueError('Error starting subprocess for fastq-multx')

        outputlines = []
#        outputlines.append('STDERR')
#        while True:
#            line = p.stderr.readline()
#            line = line.strip()
#            outputlines.append(line)
#            if not line: break
#        outputlines.append('STDOUT')
        while True:
            line = p.stdout.readline()
            line = line.strip()
            outputlines.append(line)
            if not line: break

        p.stdout.close()
        retcode = p.wait()
        print('Return code: ' + str(retcode))

        report += "\n".join(outputlines)
        self.log (console, "\n".join(outputlines))

        if p.returncode != 0:
            raise ValueError('Error running fastq-multx, return code: ' +
                             str(retcode) + '\n')

        # determine group_id_order
        #
        group_id_order = []
        if params['index_mode'] == 'manual':
            group_id_order = manual_group_id_order
        elif params['index_mode'] == 'auto-detect':
            master_barcodes_handle = open (master_barcodes_path, 'r', 0)
            for line in master_barcodes_handle.readlines():
                line = line.strip()
                if line == '':
                    continue
                row = line.split()
                if row[0] == "id" or row[0] == "ID" or row[0].startswith("#"):
                    continue
                group_id_order.append(row[0])
        elif params['index_mode'] == 'index-lane':
            for line in outputlines:
                line = line.strip()
                if line == '':
                    continue
                row = line.split()
                if row[0] == "id" or row[0] == "ID" or row[0] == '' or row[0].startswith("#") \
                  or row[0] == 'unmatched' or row[0] == 'total':
                    continue
                group_id_order.append(row[0])
        else:
            raise ValueError ("badly configured index_mode: '"+params['index_mode']+"'")


        # Collect output files and upload
        #
        paired_fwd_files   = dict()
        paired_rev_files   = dict()
        unpaired_fwd_files = dict()
        unpaired_rev_files = dict()
        unmatched_fwd_file = None
        unmatched_rev_file = None

        if 'suggest_barcodes' in params and params['suggest_barcodes'] == 1:
            pass
        else:
            for group_id in group_id_order:

                output_fwd_file_path = out_fwd_base_pattern + str(group_id) + '.fq'
                fwd_file_exists = os.path.isfile (output_fwd_file_path) \
                                      and os.path.getsize (output_fwd_file_path) != 0

                output_rev_file_path = out_rev_base_pattern + str(group_id) + '.fq'
                rev_file_exists = os.path.isfile (output_rev_file_path) \
                                      and os.path.getsize (output_rev_file_path) != 0

                if input_reads_obj_type == "KBaseFile.PairedEndLibrary":

                    if fwd_file_exists and rev_file_exists:
                        paired_fwd_files[group_id] = output_fwd_file_path
                        paired_rev_files[group_id] = output_rev_file_path
                    elif fwd_file_exists:
                        unpaired_fwd_files[group_id] = output_fwd_file_path
                    elif rev_file_exists:
                        unpaired_rev_files[group_id] = output_rev_file_path
                else:
                    if fwd_file_exists:
                        paired_fwd_files[group_id] = output_fwd_file_path

                # add unmatched
                group_id = 'unmatched'
                output_fwd_file_path = out_fwd_base_pattern + str(group_id) + '.fq'
                fwd_file_exists = os.path.isfile (output_fwd_file_path) \
                                      and os.path.getsize (output_fwd_file_path) != 0

                output_rev_file_path = out_rev_base_pattern + str(group_id) + '.fq'
                rev_file_exists = os.path.isfile (output_rev_file_path) \
                                      and os.path.getsize (output_rev_file_path) != 0

                if fwd_file_exists:
                    unmatched_fwd_file = output_fwd_file_path
                if rev_file_exists:
                    unmatched_rev_file = output_rev_file_path


        #
        # DO PAIRED LIB HYGEINE?
        #


        # upload reads
        #
        if 'suggest_barcodes' in params and params['suggest_barcodes'] == 1:
            pass
        else:

            self.log (console, "UPLOAD READS LIBS")  # DEBUG
            paired_obj_refs = []
            paired_group_ids = []
            unpaired_fwd_obj_refs = []
            unpaired_fwd_group_ids = []
            unpaired_rev_obj_refs = []
            unpaired_rev_group_ids = []
            unmatched_fwd_obj_ref = None
            unmatched_rev_obj_ref = None

            for group_id in group_id_order:

                # paired reads
                try:
                    output_fwd_paired_file_path = paired_fwd_files[group_id]
                    output_rev_paired_file_path = paired_rev_files[group_id]

                    output_obj_name = params['output_reads_name']+'_paired-'+str(group_id)
                    self.log(console, 'Uploading paired reads: '+output_obj_name)
                    paired_group_ids.append (group_id)
                    paired_obj_refs.append (readsUtils_Client.upload_reads ({ 'wsname': str(params['workspace_name']),
                                                                              'name': output_obj_name,
                                                                              # don't use sequencing_tech if you use source_reads_ref
                                                                              #'sequencing_tech': sequencing_tech,
                                                                              'source_reads_ref': params['input_reads_ref'],
                                                                              'fwd_file': output_fwd_paired_file_path,
                                                                              'rev_file': output_rev_paired_file_path
                                                                              })['obj_ref'])
                except:
                    pass

                # unpaired fwd
                try:
                    output_fwd_unpaired_file_path = unpaired_fwd_files[group_id]

                    output_obj_name = params['output_reads_name']+'_unpaired_fwd-'+str(group_id)
                    self.log(console, 'Uploading unpaired fwd reads: '+output_obj_name)
                    unpaired_fwd_group_ids.append (group_id)
                    unpaired_fwd_obj_refs.append (readsUtils_Client.upload_reads ({ 'wsname': str(params['workspace_name']),
                                                                                    'name': output_obj_name,
                                                                                    # don't use sequencing_tech if you use source_reads_ref
                                                                                    #'sequencing_tech': sequencing_tech,
                                                                                    'source_reads_ref': params['input_reads_ref'],
                                                                                    'fwd_file': output_fwd_unpaired_file_path
                                                                              })['obj_ref'])
                except:
                    pass

                # unpaired rev
                try:
                    output_rev_unpaired_file_path = unpaired_rev_files[group_id]

                    output_obj_name = params['output_reads_name']+'_unpaired_rev-'+str(group_id)
                    self.log(console, 'Uploading unpaired rev reads: '+output_obj_name)
                    unpaired_rev_group_ids.append (group_id)
                    unpaired_rev_obj_refs.append (readsUtils_Client.upload_reads ({ 'wsname': str(params['workspace_name']),
                                                                                    'name': output_obj_name,
                                                                                    # don't use sequencing_tech if you use source_reads_ref
                                                                                    #'sequencing_tech': sequencing_tech,
                                                                                    'source_reads_ref': params['input_reads_ref'],
                                                                                    'fwd_file': output_rev_unpaired_file_path
                                                                              })['obj_ref'])
                except:
                    pass

            # unmatched fwd
            if unmatched_fwd_file != None:
                output_fwd_unmatched_file_path = unmatched_fwd_file

                output_obj_name = params['output_reads_name']+'_unmatched_fwd'
                self.log(console, 'Uploading unmatched fwd reads: '+output_obj_name)
                unmatched_fwd_obj_ref = readsUtils_Client.upload_reads ({ 'wsname': str(params['workspace_name']),
                                                                          'name': output_obj_name,
                                                                          # don't use sequencing_tech if you use source_reads_ref
                                                                          #'sequencing_tech': sequencing_tech,
                                                                          'source_reads_ref': params['input_reads_ref'],
                                                                          'fwd_file': output_fwd_unmatched_file_path
                                                                              })['obj_ref']


            # unmatched rev
            if unmatched_rev_file != None:
                output_rev_unmatched_file_path = unmatched_rev_file

                output_obj_name = params['output_reads_name']+'_unmatched_rev'
                self.log(console, 'Uploading unmatched rev reads: '+output_obj_name)
                unmatched_rev_obj_ref = readsUtils_Client.upload_reads ({ 'wsname': str(params['workspace_name']),
                                                                          'name': output_obj_name,
                                                                          # don't use sequencing_tech if you use source_reads_ref
                                                                          #'sequencing_tech': sequencing_tech,
                                                                          'source_reads_ref': params['input_reads_ref'],
                                                                          'fwd_file': output_rev_unmatched_file_path
                                                                              })['obj_ref']


        # create readsSets
        #
        if 'suggest_barcodes' in params and params['suggest_barcodes'] == 1:
            pass
        else:
            self.log (console, "CREATING READS SETS")  # DEBUG
            paired_readsSet_ref       = None
            unpaired_fwd_readsSet_ref = None
            unpaired_rev_readsSet_ref = None
            unmatched_fwd_obj_ref     = None
            unmatched_rev_obj_ref     = None

            base_desc = params['desc']

            # paired end
            if len(paired_obj_refs) == 0:
                self.log (console, "No paired reads found with configured barcodes")
            else:
                self.log (console, "creating paired end readsSet")  # DEBUG
                items = []
                for lib_i,lib_ref in enumerate(paired_obj_refs):
                    label = params['output_reads_name']+'-'+str(paired_group_ids[lib_i])
                    items.append({'ref': lib_ref,
                                  'label': label
                                  #'data_attachment': ,
                                  #'info':
                                 })
                desc = base_desc
                output_readsSet_obj = { 'description': desc,
                                        'items': items
                                      }
                output_readsSet_name = str(params['output_reads_name'])
                paired_readsSet_ref = setAPI_Client.save_reads_set_v1 ({'workspace_name': str(params['workspace_name']),
                                                                        'output_object_name': output_readsSet_name,
                                                                        'data': output_readsSet_obj
                                                                        })['set_ref']

            # unpaired fwd
            if len(unpaired_fwd_obj_refs) > 0:
                self.log (console, "creating unpaired fwd readsSet")  # DEBUG
                items = []
                for lib_i,lib_ref in enumerate(unpaired_fwd_obj_refs):
                    label = params['output_reads_name']+'-'+str(unpaired_fwd_group_ids[lib_i])
                    items.append({'ref': lib_ref,
                                  'label': label
                                  #'data_attachment': ,
                                  #'info':
                                      })
                desc = base_desc+" UNPAIRED FWD"
                output_readsSet_obj = { 'description': desc,
                                        'items': items
                                        }
                output_readsSet_name = str(params['output_reads_name']+"-UNPAIRED_FWD")
                unpaired_fwd_readsSet_ref = setAPI_Client.save_reads_set_v1 ({'workspace_name': params['workspace_name'],
                                                                              'output_object_name': output_readsSet_name,
                                                                              'data': output_readsSet_obj
                                                                              })['set_ref']

            # unpaired rev
            if len(unpaired_rev_obj_refs) > 0:
                self.log (console, "creating unpaired rev readsSet")  # DEBUG
                items = []
                for lib_i,lib_ref in enumerate(unpaired_rev_obj_refs):
                    label = params['output_reads_name']+'-'+str(unpaired_rev_group_ids[lib_i])
                    items.append({'ref': lib_ref,
                                  'label': label
                                  #'data_attachment': ,
                                  #'info':
                                      })
                desc = base_desc+" UNPAIRED REV"
                output_readsSet_obj = { 'description': desc,
                                        'items': items
                                        }
                output_readsSet_name = str(params['output_reads_name']+"-UNPAIRED_REV")
                unpaired_rev_readsSet_ref = setAPI_Client.save_reads_set_v1 ({'workspace_name': params['workspace_name'],
                                                                              'output_object_name': output_readsSet_name,
                                                                              'data': output_readsSet_obj
                                                                              })['set_ref']


        # build report
        #
        self.log (console, "SAVING REPORT")  # DEBUG
        reportObj = {'objects_created':[],
                     'text_message': report}

        if paired_readsSet_ref != None:
            reportObj['objects_created'].append({'ref':paired_readsSet_ref,
                                                 'description':base_desc})
        if unpaired_fwd_readsSet_ref != None:
            reportObj['objects_created'].append({'ref':unpaired_fwd_readsSet_ref,
                                                 'description':base_desc+" UNPAIRED FWD"})
        if unpaired_rev_readsSet_ref != None:
            reportObj['objects_created'].append({'ref':unpaired_rev_readsSet_ref,
                                                 'description':base_desc+" UNPAIRED REV"})
        if unmatched_fwd_obj_ref != None:
            reportObj['objects_created'].append({'ref':unmatched_fwd_obj_ref,
                                                 'description':base_desc+" UNMATCHED FWD"})
        if unmatched_rev_obj_ref != None:
            reportObj['objects_created'].append({'ref':unmatched_rev_obj_ref,
                                                 'description':base_desc+" UNMATCHED REV"})

        # save report object
        #
        report_info = reportAPI_Client.create({'report':reportObj, 'workspace_name':params['workspace_name']})

        returnVal = { 'report_name': report_info['name'], 'report_ref': report_info['ref'] }
        #END run_Fastq_Multx

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method run_Fastq_Multx return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def run_Fastq_Join(self, ctx, params):
        """
        :param params: instance of type "run_Fastq_Join_Input"
           (run_Fastq_Join() ** ** merge overlapping mate pairs into
           SingleEnd Lib.  This sub interacts with Narrative) -> structure:
           parameter "workspace_name" of type "workspace_name" (** Common
           types), parameter "input_reads_ref" of type "data_obj_ref",
           parameter "output_reads_name" of type "data_obj_name", parameter
           "verbose" of type "bool", parameter "reverse_complement" of type
           "bool", parameter "max_perc_dist" of Long, parameter
           "min_base_overlap" of Long
        :returns: instance of type "run_Fastq_Join_Output" -> structure:
           parameter "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN run_Fastq_Join
        console = []
        self.log(console, 'Running run_Fastq_Join() with parameters: ')
        self.log(console, "\n"+pformat(params))

        token = ctx['token']
        wsClient = workspaceService(self.workspaceURL, token=token)
        headers = {'Authorization': 'OAuth '+token}
        env = os.environ.copy()
        env['KB_AUTH_TOKEN'] = token

        #SERVICE_VER = 'dev'  # DEBUG
        SERVICE_VER = 'release'

        # param checks
        required_params = ['workspace_name',
                           'input_reads_ref',
                           'output_reads_name'
                          ]
        for arg in required_params:
            if arg not in params or params[arg] == None or params[arg] == '':
                raise ValueError ("Must define required param: '"+arg+"'")

        # default params (apply defaults in exec_*OneLibarary)
        #default_params = { 'verbose': 0,
        #                   'reverse_complement': 1,
        #                   'max_perc_dist': 8,
        #                   'min_base_overlap': 6
        #                 }
        #for arg in default_params.keys():
        #    if arg not in params or params[arg] == None or params[arg] == '':
        #        params[arg] = default_params[arg]


        # load provenance
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        provenance[0]['input_ws_objects']=[str(params['input_reads_ref'])]


        # set up and run exec_Fastq_Join()
        exec_Fastq_Join_params = { 'workspace_name': str(params['workspace_name']),
                                   'input_reads_ref': str(params['input_reads_ref']),
                                   'output_reads_name': str(params['output_reads_name'])
                                 }
        optional_params = ['verbose',
                           'reverse_complement',
                           'max_perc_dist',
                           'min_base_overlap'
                          ]
        for arg in optional_params:
            if arg in params:
                exec_Fastq_Join_params[arg] = params[arg]

        # RUN
        exec_Fastq_Join_retVal = self.exec_Fastq_Join (ctx, exec_Fastq_Join_params)[0]


        # build report
        #
        reportObj = {'objects_created':[],
                     'text_message':''}

        # text report
        try:
            reportObj['text_message'] = exec_Fastq_Join_retVal['report']
        except:
            raise ValueError ("no report generated by exec_Fastq_Join()")


        # joined object
        if exec_Fastq_Join_retVal['output_joined_reads_ref'] != None:
            reportObj['objects_created'].append({'ref':exec_Fastq_Join_retVal['output_joined_reads_ref'],
                                                 'description':'Joined Reads'})
        else:
            raise ValueError ("no joined output generated by exec_Fastq_Join()")

        # unjoined object
        if exec_Fastq_Join_retVal['output_unjoined_reads_ref'] != None:
            reportObj['objects_created'].append({'ref':exec_Fastq_Join_retVal['output_unjoined_reads_ref'],
                                                 'description':'Unjoined Reads'})
        else:
            pass

        # save report object
        report = KBaseReport(self.callbackURL, token=ctx['token'], service_ver=SERVICE_VER)
        report_info = report.create({'report':reportObj, 'workspace_name':params['workspace_name']})

        returnVal = { 'report_name': report_info['name'], 'report_ref': report_info['ref'] }
        #END run_Fastq_Join

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method run_Fastq_Join return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def exec_Fastq_Join(self, ctx, params):
        """
        :param params: instance of type "run_Fastq_Join_Input"
           (run_Fastq_Join() ** ** merge overlapping mate pairs into
           SingleEnd Lib.  This sub interacts with Narrative) -> structure:
           parameter "workspace_name" of type "workspace_name" (** Common
           types), parameter "input_reads_ref" of type "data_obj_ref",
           parameter "output_reads_name" of type "data_obj_name", parameter
           "verbose" of type "bool", parameter "reverse_complement" of type
           "bool", parameter "max_perc_dist" of Long, parameter
           "min_base_overlap" of Long
        :returns: instance of type "exec_Fastq_Join_Output" -> structure:
           parameter "output_joined_reads_ref" of type "data_obj_ref",
           parameter "output_unjoined_reads_ref" of type "data_obj_ref"
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN exec_Fastq_Join
        console = []
        self.log(console, 'Running exec_Fastq_Join() with parameters: ')
        self.log(console, "\n"+pformat(params))
        report = ''
        returnVal = dict()
        returnVal['output_joined_reads_ref']   = None
        returnVal['output_unjoined_reads_ref'] = None

        token = ctx['token']
        wsClient = workspaceService(self.workspaceURL, token=token)
        headers = {'Authorization': 'OAuth '+token}
        env = os.environ.copy()
        env['KB_AUTH_TOKEN'] = token

        # param checks
        required_params = ['workspace_name',
                           'input_reads_ref',
                           'output_reads_name'
                          ]
        for arg in required_params:
            if arg not in params or params[arg] == None or params[arg] == '':
                raise ValueError ("Must define required param: '"+arg+"'")

        # default params (apply defaults in exec_*OneLibarary)
        #default_params = { 'verbose': 0,
        #                   'reverse_complement': 1,
        #                   'max_perc_dist': 8,
        #                   'min_base_overlap': 6
        #                 }
        #for arg in default_params.keys():
        #    arg not in params or params[arg] == None or params[arg] == '':
        #        params[arg] = default_params[arg]


        # load provenance
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        # add additional info to provenance here, in this case the input data object reference
        provenance[0]['input_ws_objects']=[str(params['input_reads_ref'])]

        # Determine whether read library or read set is input object
        #
        try:
            # object_info tuple
            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)

            input_reads_obj_info = wsClient.get_object_info_new ({'objects':[{'ref':params['input_reads_ref']}]})[0]
            input_reads_obj_type = input_reads_obj_info[TYPE_I]
            input_reads_obj_type = re.sub ('-[0-9]+\.[0-9]+$', "", input_reads_obj_type)  # remove trailing version
            #input_reads_obj_version = input_reads_obj_info[VERSION_I]  # this is object version, not type version
        except Exception as e:
            raise ValueError('Unable to get read library object from workspace: (' + str(params['input_reads_ref']) +')' + str(e))

        acceptable_types = ["KBaseSets.ReadsSet", "KBaseFile.PairedEndLibrary"]
        if input_reads_obj_type not in acceptable_types:
            raise ValueError ("Input reads of type: '"+input_reads_obj_type+"'.  Must be one of "+", ".join(acceptable_types))


        # get set
        #
        readsSet_ref_list = []
        readsSet_names_list = []
        if input_reads_obj_type != "KBaseSets.ReadsSet":
            readsSet_ref_list = [params['input_reads_ref']]
            readsSet_names_list = [params['output_reads_name']]
        else:
            try:
                #setAPI_Client = SetAPI (url=self.callbackURL, token=ctx['token'])  # for SDK local.  doesn't work for SetAPI
                setAPI_Client = SetAPI (url=self.serviceWizardURL, token=ctx['token'])  # for dynamic service
                input_readsSet_obj = setAPI_Client.get_reads_set_v1 ({'ref':params['input_reads_ref'],'include_item_info':1})

            except Exception as e:
                raise ValueError('SetAPI FAILURE: Unable to get read library set object from workspace: (' + str(params['input_reads_ref'])+")\n" + str(e))
            for readsLibrary_obj in input_readsSet_obj['data']['items']:
                readsSet_ref_list.append(readsLibrary_obj['ref'])
                NAME_I = 1
                readsSet_names_list.append(readsLibrary_obj['info'][NAME_I])


        # Iterate through readsLibrary memebers of set
        #
        report = ''
        joined_readsSet_ref    = None
        unjoined_readsSet_ref  = None
        joined_readsLib_refs   = []
        unjoined_readsLib_refs = []

        for reads_item_i,input_reads_library_ref in enumerate(readsSet_ref_list):
            exec_Fastq_Join_params = { 'workspace_name': params['workspace_name'],
                                       'input_reads_ref': input_reads_library_ref
                                     }
            if input_reads_obj_type != "KBaseSets.ReadsSet":
                exec_Fastq_Join_params['output_reads_name'] = params['output_reads_name']
            else:
                exec_Fastq_Join_params['output_reads_name'] = readsSet_names_list[reads_item_i]

            optional_params = ['verbose',
                               'reverse_complement',
                               'max_perc_dist',
                               'min_base_overlap'
                               ]
            for arg in optional_params:
                if arg in params:
                    exec_Fastq_Join_params[arg] = params[arg]

            msg = "\n\nRUNNING Fastq_Join ON LIBRARY: "+str(input_reads_library_ref)+" "+str(readsSet_names_list[reads_item_i])+"\n"
            msg += "----------------------------------------------------------------------------\n"
            report += msg
            self.log (console, msg)

            # RUN
            exec_Fastq_Join_OneLibrary_retVal = self.exec_Fastq_Join_OneLibrary (ctx, exec_Fastq_Join_params)[0]

            report += exec_Fastq_Join_OneLibrary_retVal['report']+"\n\n"
            joined_readsLib_refs.append (exec_Fastq_Join_OneLibrary_retVal['output_joined_reads_ref'])
            unjoined_readsLib_refs.append (exec_Fastq_Join_OneLibrary_retVal['output_unjoined_reads_ref'])


        # Just one Library
        if input_reads_obj_type != "KBaseSets.ReadsSet":

            # create return output object
            returnVal = { 'report': report,
                          'output_joined_reads_ref': joined_readsLib_refs[0],
                          'output_unjoined_reads_ref': unjoined_readsLib_refs[0]
                        }
        # ReadsSet
        else:

            # save joined readsSet
            some_joined_output_created = False
            items = []
            for i,lib_ref in enumerate(joined_readsLib_refs):   # FIX: assumes order maintained
                if lib_ref == None:
                    #items.append(None)  # can't have 'None' items in ReadsSet
                    continue
                else:
                    some_joined_output_created = True
                    try:
                        label = input_readsSet_obj['data']['items'][i]['label']
                    except:
                        NAME_I = 1
                        label = wsClient.get_object_info_new ({'objects':[{'ref':lib_ref}]})[0][NAME_I]
                    label = label + "_joined"

                    items.append({'ref': lib_ref,
                                  'label': label
                                  #'data_attachment': ,
                                  #'info':
                                      })
            if some_joined_output_created:
                reads_desc_ext = " Fastq_Join joined reads"
                reads_name_ext = "_joined"
                output_readsSet_obj = { 'description': input_readsSet_obj['data']['description']+reads_desc_ext,
                                        'items': items
                                        }
                output_readsSet_name = str(params['output_reads_name'])+reads_name_ext
                joined_readsSet_ref = setAPI_Client.save_reads_set_v1 ({'workspace_name': params['workspace_name'],
                                                                        'output_object_name': output_readsSet_name,
                                                                        'data': output_readsSet_obj
                                                                        })['set_ref']
            else:
                raise ValueError ("No joined output created")


            # save unjoined readsSet
            some_unjoined_output_created = False
            if len(unjoined_readsLib_refs) > 0:
                items = []
                for i,lib_ref in enumerate(unjoined_readsLib_refs):  # FIX: assumes order maintained
                    if lib_ref == None:
                        #items.append(None)  # can't have 'None' items in ReadsSet
                        continue
                    else:
                        some_unjoined_output_created = True
                        try:
                            if len(unjoined_readsLib_refs) == len(input_readsSet_obj['data']['items']):
                                label = input_readsSet_obj['data']['items'][i]['label']
                            else:
                                NAME_I = 1
                                label = wsClient.get_object_info_new ({'objects':[{'ref':lib_ref}]})[0][NAME_I]
                        except:
                            NAME_I = 1
                            label = wsClient.get_object_info_new ({'objects':[{'ref':lib_ref}]})[0][NAME_I]
                        label = label + "_unjoined"

                        items.append({'ref': lib_ref,
                                      'label': label
                                      #'data_attachment': ,
                                      #'info':
                                          })
                if some_unjoined_output_created:
                    output_readsSet_obj = { 'description': input_readsSet_obj['data']['description']+" Fastq_Join unjoined reads",
                                            'items': items
                                            }
                    output_readsSet_name = str(params['output_reads_name'])+'_unjoined'
                    unjoined_readsSet_ref = setAPI_Client.save_reads_set_v1 ({'workspace_name': params['workspace_name'],
                                                                              'output_object_name': output_readsSet_name,
                                                                              'data': output_readsSet_obj
                                                                              })['set_ref']
                else:
                    self.log (console, "no unjoined readsLibraries created")
                    unjoined_readsSet_ref = None

            # create return output object
            returnVal = { 'report': report,
                          'output_joined_reads_ref': joined_readsSet_ref,
                          'output_unjoined_reads_ref': unjoined_readsSet_ref
                        }
        #END exec_Fastq_Join

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method exec_Fastq_Join return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def exec_Fastq_Join_OneLibrary(self, ctx, params):
        """
        :param params: instance of type "run_Fastq_Join_Input"
           (run_Fastq_Join() ** ** merge overlapping mate pairs into
           SingleEnd Lib.  This sub interacts with Narrative) -> structure:
           parameter "workspace_name" of type "workspace_name" (** Common
           types), parameter "input_reads_ref" of type "data_obj_ref",
           parameter "output_reads_name" of type "data_obj_name", parameter
           "verbose" of type "bool", parameter "reverse_complement" of type
           "bool", parameter "max_perc_dist" of Long, parameter
           "min_base_overlap" of Long
        :returns: instance of type "exec_Fastq_Join_Output" -> structure:
           parameter "output_joined_reads_ref" of type "data_obj_ref",
           parameter "output_unjoined_reads_ref" of type "data_obj_ref"
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN exec_Fastq_Join_OneLibrary
        console = []
        self.log(console, 'Running exec_Fastq_Join_OneLibrary() with parameters: ')
        self.log(console, "\n"+pformat(params))
        report = ''
        retVal = dict()
        retVal['output_joined_reads_ref'] = None
        retVal['output_unjoined_reads_ref'] = None

        token = ctx['token']
        wsClient = workspaceService(self.workspaceURL, token=token)
        headers = {'Authorization': 'OAuth '+token}
        env = os.environ.copy()
        env['KB_AUTH_TOKEN'] = token

        # param checks
        required_params = ['workspace_name',
                           'input_reads_ref',
                           'output_reads_name'
                          ]
        for arg in required_params:
            if arg not in params or params[arg] == None or params[arg] == '':
                raise ValueError ("Must define required param: '"+arg+"'")

        # default params
        default_params = { 'verbose': 0,
                           'reverse_complement': 1,
                           'max_perc_dist': 8,
                           'min_base_overlap': 6
                         }
        for arg in default_params.keys():
            if arg not in params or params[arg] == None or params[arg] == '':
                params[arg] = default_params[arg]


        # load provenance
        provenance = [{}]
        if 'provenance' in ctx:
            provenance = ctx['provenance']
        # add additional info to provenance here, in this case the input data object reference
        provenance[0]['input_ws_objects']=[str(params['input_reads_ref'])]


        # Determine whether read library is of correct type
        #
        try:
            # object_info tuple
            [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)

            input_reads_obj_info = wsClient.get_object_info_new ({'objects':[{'ref':params['input_reads_ref']}]})[0]
            input_reads_obj_type = input_reads_obj_info[TYPE_I]
            input_reads_obj_type = re.sub ('-[0-9]+\.[0-9]+$', "", input_reads_obj_type)  # remove trailing version
            #input_reads_obj_version = input_reads_obj_info[VERSION_I]  # this is object version, not type version

        except Exception as e:
            raise ValueError('Unable to get read library object from workspace: (' + str(params['input_reads_ref']) +')' + str(e))
        acceptable_types = ["KBaseFile.PairedEndLibrary"]
        if input_reads_obj_type not in acceptable_types:
            raise ValueError ("Input reads of type: '"+input_reads_obj_type+"'.  Must be one of "+", ".join(acceptable_types))


        # Instantiate ReadsUtils
        #
        try:
            readsUtils_Client = ReadsUtils (url=self.callbackURL, token=ctx['token'])  # SDK local

            readsLibrary = readsUtils_Client.download_reads ({'read_libraries': [params['input_reads_ref']],
                                                             'interleaved': 'false'
                                                             })
        except Exception as e:
            raise ValueError('Unable to get read library object from workspace: (' + str(params['input_reads_ref']) +")\n" + str(e))


        # Download reads Libs to FASTQ files
        input_fwd_file_path = readsLibrary['files'][params['input_reads_ref']]['files']['fwd']
        input_rev_file_path = readsLibrary['files'][params['input_reads_ref']]['files']['rev']
        sequencing_tech     = readsLibrary['files'][params['input_reads_ref']]['sequencing_tech']


        #
        # LET'S ROCK!!!
        #

        # output paths
        timestamp = int((datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()*1000)
        output_dir = os.path.join(self.scratch,'output.'+str(timestamp))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # output file pattern
        out_base_pattern = output_dir+'/'+'fastq_join_output.'
        out_pattern      = out_base_pattern+'%.fq'


        # Build Command
        cmd = [self.FASTQ_JOIN]

        if params['verbose'] == 1:
            verbose_stitch_len_report_path = output_dir+'/'+'verbose_stich_report.txt'
            cmd.append('-v')
            cmd.append(verbose_stitch_len_report_path)

        if params['reverse_complement'] != 1:
            cmd.append('-R')

        cmd.append ('-p')
        cmd.append (str(params['max_perc_dist']))
        cmd.append ('-m')
        cmd.append (str(params['min_base_overlap']))

        # file args
        cmd.append (input_fwd_file_path)
        cmd.append (input_rev_file_path)
        cmd.append ('-o')
        cmd.append (out_pattern)


        # Run Fastq_Join
        #
        self.log(console, "Starting Fastq_Join with command:\n")
        self.log(console, " ".join(cmd))

        cmdProcess = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        outputlines = []
        while True:
            line = cmdProcess.stdout.readline()
            outputlines.append(line)
            if not line: break
            self.log(console, line.replace('\n', ''))

        cmdProcess.stdout.close()
        cmdProcess.wait()
        self.log(console, 'return code: ' + str(cmdProcess.returncode) + '\n')
        if cmdProcess.returncode != 0:
            raise ValueError('Error running Fastq_Join, return code: ' +
                             str(cmdProcess.returncode) + '\n')

        #report += "cmdstring: " + cmdstring + " stdout: " + stdout + " stderr " + stderr

        #get read counts
        #match = re.search(r'Input Read Pairs: (\d+).*?Both Surviving: (\d+).*?Forward Only Surviving: (\d+).*?Reverse Only Surviving: (\d+).*?Dropped: (\d+)', report)
        #input_read_count = match.group(1)
        #read_count_paired = match.group(2)
        #read_count_forward_only = match.group(3)
        #read_count_reverse_only = match.group(4)
        #read_count_dropped = match.group(5)

        #report = "\n".join( ('Input Read Pairs: '+ input_read_count,
        #                     'Both Surviving: '+ read_count_paired,
        #                     'Forward Only Surviving: '+ read_count_forward_only,
        #                     'Reverse Only Surviving: '+ read_count_reverse_only,
        #                     'Dropped: '+ read_count_dropped) )

        report += "\n".join(outputlines)

        if params['verbose'] == 1:
            report += "\n\nVERBOSE STITCH LENGTH REPORT:\n"
            with open (verbose_stich_len_report_path, 'r', 0) as verbose_file_handle:
                report += "".join (verbose_file_handle.readlines())


        # upload joined reads
        output_joined_file_path = out_base_pattern+'join.fq'
        if not os.path.isfile (output_joined_file_path) \
                or os.path.getsize (output_joined_file_path) == 0:

            retVal['output_joined_reads_ref'] = None
        else:
            output_obj_name = params['output_reads_name']+'_joined'
            self.log(console, 'Uploading joined reads: '+output_obj_name)
            retVal['output_joined_reads_ref'] = readsUtils_Client.upload_reads ({ 'wsname': str(params['workspace_name']),
                                                                                  'name': output_obj_name,
                                                                                  # don't use sequencing_tech as well as source_reads_ref
                                                                                  #'sequencing_tech': sequencing_tech,
                                                                                  'source_reads_ref': params['input_reads_ref'],
                                                                                  'fwd_file': output_joined_file_path
                                                                                  })['obj_ref']


        # upload unjoined reads
        output_unjoined_fwd_file_path = out_base_pattern+'un1.fq'
        output_unjoined_rev_file_path = out_base_pattern+'un2.fq'
        if not os.path.isfile (output_unjoined_fwd_file_path) \
                or os.path.getsize (output_unjoined_fwd_file_path) == 0 \
                or not os.path.isfile (output_unjoined_rev_file_path) \
                or os.path.getsize (output_unjoined_rev_file_path) == 0:

            retVal['output_unjoined_reads_ref'] = None
        else:
            output_obj_name = params['output_reads_name']+'_unjoined'
            self.log(console, '\nUploading unjoined reads: '+output_obj_name)
            retVal['output_unjoined_reads_ref'] = readsUtils_Client.upload_reads ({ 'wsname': str(params['workspace_name']),
                                                                                    'name': output_obj_name,
                                                                                    # don't use sequencing_tech as well as source_reads_ref
                                                                                    #'sequencing_tech': sequencing_tech,
                                                                                    'source_reads_ref': params['input_reads_ref'],
                                                                                    'fwd_file': output_unjoined_fwd_file_path,
                                                                                    'rev_file': output_unjoined_rev_file_path
                                                                                    })['obj_ref']


        # return created objects
        #
        returnVal = { 'report': report,
                      'output_joined_reads_ref': retVal['output_joined_reads_ref'],
                      'output_unjoined_reads_ref': retVal['output_unjoined_reads_ref']
                    }
        #END exec_Fastq_Join_OneLibrary

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method exec_Fastq_Join_OneLibrary return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]

    def exec_Determine_Phred(self, ctx, params):
        """
        :param params: instance of type "exec_Determine_Phred_Input"
           (exec_Determine_Phred() ** ** determine qual score regime.  Either
           "phred33" or "phred64") -> structure: parameter "workspace_name"
           of type "workspace_name" (** Common types), parameter
           "input_reads_ref" of type "data_obj_ref", parameter
           "input_reads_file" of type "file_path"
        :returns: instance of type "exec_Determine_Phred_Output" ->
           structure: parameter "phred_type" of String
        """
        # ctx is the context object
        # return variables are: returnVal
        #BEGIN exec_Determine_Phred
        console = []
        report = ''
        self.log(console, 'Running KButil_Determine_Phred() with parameters: ')
        self.log(console, "\n"+pformat(params))

        token = ctx['token']
        wsClient = workspaceService(self.workspaceURL, token=token)
        headers = {'Authorization': 'OAuth '+token}
        env = os.environ.copy()
        env['KB_AUTH_TOKEN'] = token

        #SERVICE_VER = 'dev'  # DEBUG
        SERVICE_VER = 'release'

        # param checks
        if 'input_reads_ref' not in params and 'input_reads_file' not in params:
            raise ValueError ("Must define either param: 'input_reads_ref' or 'input_reads_file'")

        # get file
        if 'input_reads_file' in params:
            this_input_fwd_path = params['input_reads_file']
        else:
            # Determine whether read library is of correct type
            try:
                # object_info tuple
                [OBJID_I, NAME_I, TYPE_I, SAVE_DATE_I, VERSION_I, SAVED_BY_I, WSID_I, WORKSPACE_I, CHSUM_I, SIZE_I, META_I] = range(11)

                input_reads_ref = params['input_reads_ref']
                input_reads_obj_info = wsClient.get_object_info_new ({'objects':[{'ref':input_reads_ref}]})[0]
                input_reads_obj_type = input_reads_obj_info[TYPE_I]
                input_reads_obj_type = re.sub ('-[0-9]+\.[0-9]+$', "", input_reads_obj_type)  # remove trailing version
            #input_reads_obj_version = input_reads_obj_info[VERSION_I]  # this is object version, not type version

            except Exception as e:
                raise ValueError('Unable to get read library object info from workspace: (' + str(input_reads_ref) +')' + str(e))

            acceptable_types = ["KBaseFile.PairedEndLibrary", "KBaseFile.SingleEndLibrary"]
            if input_reads_obj_type not in acceptable_types:
                raise ValueError ("Input reads of type: '"+input_reads_obj_type+"'.  Must be one of "+", ".join(acceptable_types))


            # Download Reads
            self.log (console, "DOWNLOADING READS")  # DEBUG
            try:
                readsUtils_Client = ReadsUtils (url=self.callbackURL, token=ctx['token'])  # SDK local
            except Exception as e:
                raise ValueError('Unable to get ReadsUtils Client' +"\n" + str(e))
            try:
                readsLibrary = readsUtils_Client.download_reads ({'read_libraries': [input_reads_ref],
                                                                  'interleaved': 'false'
                                                                  })
            except Exception as e:
                raise ValueError('Unable to download read library sequences from workspace: (' + str(input_reads_ref) +")\n" + str(e))

            this_input_fwd_path = readsLibrary['files'][this_input_reads_ref]['files']['fwd']


        # Run determine-phred
        determine_phred_cmd = []
        determine_phred_cmd.append(self.DETERMINE_PHRED)
        determine_phred_cmd.append(this_input_fwd_path)
        print('running determine-phred:')
        print('    '+' '.join(determine_phred_cmd))
        #p = subprocess.Popen(" ".join(determine_phred_cmd), cwd=self.scratch, shell=True)
        #p = subprocess.Popen(" ".join(determine_phred_cmd), cwd=self.scratch, shell=False)
        p = subprocess.Popen(determine_phred_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.scratch)
        phred_regime = p.stdout.readline()
        phred_regime.replace('\n', '')
        p.stdout.close()

        retcode = p.wait()
        print('Return code: ' + str(retcode))
        if p.returncode != 0:
            raise ValueError('Error running Determine_Phred(), return code: ' +
                             str(retcode) + '\n')

        returnVal = { 'phred_type': phred_regime }
        #END exec_Determine_Phred

        # At some point might do deeper type checking...
        if not isinstance(returnVal, dict):
            raise ValueError('Method exec_Determine_Phred return value ' +
                             'returnVal is not type dict as required.')
        # return the results
        return [returnVal]
    def status(self, ctx):
        #BEGIN_STATUS
        returnVal = {'state': "OK", 'message': "", 'version': self.VERSION,
                     'git_url': self.GIT_URL, 'git_commit_hash': self.GIT_COMMIT_HASH}
        #END_STATUS
        return [returnVal]
