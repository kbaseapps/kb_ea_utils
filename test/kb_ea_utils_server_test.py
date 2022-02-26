# -*- coding: utf-8 -*-
import unittest
import os
import json
import shutil
import time
import requests

requests.packages.urllib3.disable_warnings()

from os import environ
try:
    from ConfigParser import ConfigParser  # py2
except:
    from configparser import ConfigParser  # py3

from pprint import pprint

from requests_toolbelt import MultipartEncoder

from biokbase.workspace.client import Workspace as workspaceService
from biokbase.AbstractHandle.Client import AbstractHandle as HandleService
from installed_clients.DataFileUtilClient import DataFileUtil
from kb_ea_utils.authclient import KBaseAuth as _KBaseAuth
from kb_ea_utils.kb_ea_utilsImpl import kb_ea_utils
from kb_ea_utils.kb_ea_utilsServer import MethodContext

class kb_ea_utilsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = environ.get('KB_AUTH_TOKEN', None)
        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_ea_utils'):
            cls.cfg[nameval[0]] = nameval[1]
        authServiceUrl = cls.cfg.get('auth-service-url',
                "https://kbase.us/services/authorization/Sessions/Login")
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'kb_ea_utils',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})

        config_file = environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('kb_ea_utils'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.wsURL = cls.cfg['workspace-url']
        cls.shockURL = cls.cfg['shock-url']
        cls.handleURL = cls.cfg['handle-service-url']
        cls.serviceWizardURL = cls.cfg['service-wizard-url']

        cls.wsClient = workspaceService(cls.wsURL, token=token)
        cls.serviceImpl = kb_ea_utils(cls.cfg)

        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        cls.dfu = DataFileUtil(cls.callback_url)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

        if hasattr(cls, 'shock_ids'):
            for shock_id in cls.shock_ids:
                print('Deleting SHOCK node: '+str(shock_id))
                cls.delete_shock_node(shock_id)

    def getWsClient(self):
        return self.__class__.wsClient

    def getWsName(self):
        if hasattr(self.__class__, 'wsName'):
            return self.__class__.wsName
        suffix = int(time.time() * 1000)
        wsName = "test_kb_ea_utils_" + str(suffix)
        ret = self.getWsClient().create_workspace({'workspace': wsName})
        self.__class__.wsName = wsName
        return wsName

    def getImpl(self):
        return self.__class__.serviceImpl

    def getContext(self):
        return self.__class__.ctx


    # @classmethod
    # def upload_file_to_shock(cls, file_path):
    #     """
    #     Use HTTP multi-part POST to save a file to a SHOCK instance.
    #     """
    #
    #     header = dict()
    #     header["Authorization"] = "Oauth {0}".format(cls.ctx['token'])
    #
    #     if file_path is None:
    #         raise Exception("No file given for upload to SHOCK!")
    #
    #     with open(os.path.abspath(file_path), 'rb') as dataFile:
    #         files = {'upload': dataFile}
    #         response = requests.post(
    #             cls.shockURL + '/node', headers=header, files=files,
    #             stream=True, allow_redirects=True, timeout=30)
    #
    #     if not response.ok:
    #         response.raise_for_status()
    #
    #     result = response.json()
    #
    #     if result['error']:
    #         raise Exception(result['error'][0])
    #     else:
    #         shock_id = result['data']['id']
    #         if not hasattr(cls, 'shock_ids'):
    #             cls.shock_ids = []
    #         cls.shock_ids.append(shock_id)
    #
    #         return result["data"]

    @classmethod
    def upload_file_to_shock(cls, file_path):
        """
        Use DataFileUtil.file_to_shock() save a file to a SHOCK instance.
        """

        if file_path is None:
            raise Exception("No file given for upload to SHOCK!")

        # copy file to where DFU can see it (can only see scratch)
        src_file_basename = os.path.basename(file_path)
        shared_file_path = os.path.join(cls.scratch, src_file_basename)
        shutil.copy2(file_path, shared_file_path)

        # Upload files to shock
        try:
            shock_info = cls.dfu.file_to_shock({
                'file_path': shared_file_path,
                'make_handle': 1
            })
        except Exception as e:
            raise ValueError('Unable to store ' + file_path + str(e))
            #traceback.format_exc() # to get the full stack trace

        # remember shock info
        if not hasattr(cls, 'shock_ids'):
            cls.shock_ids = []
        cls.shock_ids.append(shock_info['shock_id'])
        # print("!!!!shock_info",shock_info)
        return shock_info


    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.ctx['token'])}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)


    @classmethod
    def delete_shock_node(cls, node_id):
        header = {'Authorization': 'Oauth {0}'.format(cls.ctx['token'])}
        requests.delete(cls.shockURL + '/node/' + node_id, headers=header,
                        allow_redirects=True)
        print('Deleted shock node ' + node_id)


    def getSingleEndLibInfo(self, read_lib_basename, lib_i=0):
        if hasattr(self.__class__, 'singleEndLibInfo_list'):
            try:
                info = self.__class__.singleEndLibInfo_list[lib_i]
                name = self.__class__.singleEndLibName_list[lib_i]
                if info != None:
                    if name != read_lib_basename:
                        self.__class__.singleEndLib_SetInfo[lib_i] = None
                        self.__class__.singleEndLib_SetName[lib_i] = None
                    else:
                        return info
            except:
                pass

        # 1) upload files to shock
        token = self.ctx['token']
        forward_shock_file = self.upload_file_to_shock('data/'+read_lib_basename+'.fwd.fq')
        #pprint(forward_shock_file)

        # 2) create handle
        hs = HandleService(url=self.handleURL, token=token)
        forward_handle = hs.persist_handle({
                                        'id' : forward_shock_file['shock_id'],
                                        'type' : 'shock',
                                        'url' : self.shockURL,
                                        'file_name': forward_shock_file['node_file_name'],
                                        'remote_md5': forward_shock_file['handle']['remote_md5']})

        # 3) save to WS
        single_end_library = {
            'lib': {
                'file': {
                    'hid':forward_handle,
                    'file_name': forward_shock_file['node_file_name'],
                    'id': forward_shock_file['shock_id'],
                    'url': self.shockURL,
                    'type':'shock',
                    'remote_md5':forward_shock_file['handle']['remote_md5']
                },
                'encoding':'UTF8',
                'type':'fastq',
                'size':forward_shock_file['size']
            },
            'sequencing_tech':'artificial reads'
        }

        new_obj_info = self.wsClient.save_objects({
                        'workspace':self.getWsName(),
                        'objects':[
                            {
                                'type':'KBaseFile.SingleEndLibrary',
                                'data':single_end_library,
                                'name':'test-'+str(lib_i)+'.se.reads',
                                'meta':{},
                                'provenance':[
                                    {
                                        'service':'kb_ea_utils',
                                        'method':'test_run_ea-utils'
                                    }
                                ]
                            }]
                        })[0]

        # store it
        if not hasattr(self.__class__, 'singleEndLibInfo_list'):
            self.__class__.singleEndLibInfo_list = []
            self.__class__.singleEndLibName_list = []
        for i in range(lib_i+1):
            try:
                assigned = self.__class__.singleEndLibInfo_list[i]
            except:
                self.__class__.singleEndLibInfo_list.append(None)
                self.__class__.singleEndLibName_list.append(None)

        self.__class__.singleEndLibInfo_list[lib_i] = new_obj_info
        self.__class__.singleEndLibName_list[lib_i] = read_lib_basename
        return new_obj_info


    def getPairedEndLibInfo(self, read_lib_basename, lib_i=0):
        if hasattr(self.__class__, 'pairedEndLibInfo_list'):
            try:
                info = self.__class__.pairedEndLibInfo_list[lib_i]
                name = self.__class__.pairedEndLibName_list[lib_i]
                if info != None:
                    if name != read_lib_basename:
                        self.__class__.singleEndLibInfo_list[lib_i] = None
                        self.__class__.singleEndLibName_list[lib_i] = None
                    else:
                        return info
            except:
                pass

        # 1) upload files to shock
        token = self.ctx['token']
        forward_shock_file = self.upload_file_to_shock('data/'+read_lib_basename+'.fwd.fq')
        reverse_shock_file = self.upload_file_to_shock('data/'+read_lib_basename+'.rev.fq')
        #pprint(forward_shock_file)
        #pprint(reverse_shock_file)

        # 2) create handle
        hs = HandleService(url=self.handleURL, token=token)
        forward_handle = hs.persist_handle({
                                        'id' : forward_shock_file['shock_id'],
                                        'type' : 'shock',
                                        'url' : self.shockURL,
                                        'file_name': forward_shock_file['node_file_name'],
                                        'remote_md5': forward_shock_file['handle']['remote_md5']})

        reverse_handle = hs.persist_handle({
                                        'id' : reverse_shock_file['shock_id'],
                                        'type' : 'shock',
                                        'url' : self.shockURL,
                                        'file_name': reverse_shock_file['node_file_name'],
                                        'remote_md5': reverse_shock_file['handle']['remote_md5']})

        # 3) save to WS
        paired_end_library = {
            'lib1': {
                'file': {
                    'hid':forward_handle,
                    'file_name': forward_shock_file['node_file_name'],
                    'id': forward_shock_file['shock_id'],
                    'url': self.shockURL,
                    'type':'shock',
                    'remote_md5':forward_shock_file['handle']['remote_md5']
                },
                'encoding':'UTF8',
                'type':'fastq',
                'size':forward_shock_file['size']
            },
            'lib2': {
                'file': {
                    'hid':reverse_handle,
                    'file_name': reverse_shock_file['node_file_name'],
                    'id': reverse_shock_file['shock_id'],
                    'url': self.shockURL,
                    'type':'shock',
                    'remote_md5':reverse_shock_file['handle']['remote_md5']
                },
                'encoding':'UTF8',
                'type':'fastq',
                'size':reverse_shock_file['size']
            },
            'interleaved':0,
            'sequencing_tech':'artificial reads'
        }

        new_obj_info = self.wsClient.save_objects({
                        'workspace':self.getWsName(),
                        'objects':[
                            {
                                'type':'KBaseFile.PairedEndLibrary',
                                'data':paired_end_library,
                                'name':'test-'+str(lib_i)+'.pe.reads',
                                'meta':{},
                                'provenance':[
                                    {
                                        'service':'kb_ea_utils',
                                        'method':'test_run_ea-utils'
                                    }
                                ]
                            }]
                        })[0]

        # store it
        if not hasattr(self.__class__, 'pairedEndLibInfo_list'):
            self.__class__.pairedEndLibInfo_list = []
            self.__class__.pairedEndLibName_list = []
        for i in range(lib_i+1):
            try:
                assigned = self.__class__.pairedEndLibInfo_list[i]
            except:
                self.__class__.pairedEndLibInfo_list.append(None)
                self.__class__.pairedEndLibName_list.append(None)

        self.__class__.pairedEndLibInfo_list[lib_i] = new_obj_info
        self.__class__.pairedEndLibName_list[lib_i] = read_lib_basename
        return new_obj_info


    def getPairedEndInterleavedLibInfo(self, read_lib_basename, lib_i=0):
        if hasattr(self.__class__, 'pairedEndLibInfo_list'):
            try:
                info = self.__class__.pairedEndLibInfo_list[lib_i]
                name = self.__class__.pairedEndLibName_list[lib_i]
                if info != None:
                    if name != read_lib_basename:
                        self.__class__.singleEndLibInfo_list[lib_i] = None
                        self.__class__.singleEndLibName_list[lib_i] = None
                    else:
                        return info
            except:
                pass

        # 1) upload files to shock
        token = self.ctx['token']
        forward_shock_file = self.upload_file_to_shock('data/'+read_lib_basename+'.inter.fq')
        #pprint(forward_shock_file)
        #pprint(reverse_shock_file)

        # 2) create handle
        hs = HandleService(url=self.handleURL, token=token)
        forward_handle = hs.persist_handle({
                                        'id' : forward_shock_file['shock_id'],
                                        'type' : 'shock',
                                        'url' : self.shockURL,
                                        'file_name': forward_shock_file['node_file_name'],
                                        'remote_md5': forward_shock_file['handle']['remote_md5']})

        # 3) save to WS
        paired_end_library = {
            'lib1': {
                'file': {
                    'hid':forward_handle,
                    'file_name': forward_shock_file['node_file_name'],
                    'id': forward_shock_file['shock_id'],
                    'url': self.shockURL,
                    'type':'shock',
                    'remote_md5':forward_shock_file['handle']['remote_md5']
                },
                'encoding':'UTF8',
                'type':'fastq',
                'size':forward_shock_file['size']
            },
            'interleaved':1,
            'sequencing_tech':'artificial reads'
        }

        new_obj_info = self.wsClient.save_objects({
                        'workspace':self.getWsName(),
                        'objects':[
                            {
                                'type':'KBaseFile.PairedEndLibrary',
                                'data':paired_end_library,
                                'name':'test-'+str(lib_i)+'.pe.reads',
                                'meta':{},
                                'provenance':[
                                    {
                                        'service':'kb_ea_utils',
                                        'method':'test_run_ea-utils'
                                    }
                                ]
                            }]
                        })[0]

        # store it
        if not hasattr(self.__class__, 'pairedEndLibInfo_list'):
            self.__class__.pairedEndLibInfo_list = []
            self.__class__.pairedEndLibName_list = []
        for i in range(lib_i+1):
            try:
                assigned = self.__class__.pairedEndLibInfo_list[i]
            except:
                self.__class__.pairedEndLibInfo_list.append(None)
                self.__class__.pairedEndLibName_list.append(None)

        self.__class__.pairedEndLibInfo_list[lib_i] = new_obj_info
        self.__class__.pairedEndLibName_list[lib_i] = read_lib_basename
        return new_obj_info


    # call this method to get the WS object info of a Single End Library Set (will
    # upload the example data if this is the first time the method is called during tests)
    def getSingleEndLib_SetInfo(self, read_libs_basename_list, refresh=False):
        if hasattr(self.__class__, 'singleEndLib_SetInfo'):
            try:
                info = self.__class__.singleEndLib_SetInfo
                if info != None:
                    if refresh:
                        self.__class__.singleEndLib_SetInfo = None
                    else:
                        return info
            except:
                pass

        # build items and save each PairedEndLib
        items = []
        for lib_i,read_lib_basename in enumerate (read_libs_basename_list):
            label    = read_lib_basename
            lib_info = self.getSingleEndLibInfo (read_lib_basename, lib_i)
            lib_ref  = str(lib_info[6])+'/'+str(lib_info[0])
            print ("LIB_REF["+str(lib_i)+"]: "+lib_ref+" "+read_lib_basename)  # DEBUG

            items.append({'ref': lib_ref,
                          'label': label
                          #'data_attachment': ,
                          #'info':
                         })

        # save readsset
        desc = 'test ReadsSet'
        readsSet_obj = { 'description': desc,
                         'items': items
                       }
        name = 'TEST_READSET'

        new_obj_info = self.wsClient.save_objects({
                        'workspace':self.getWsName(),
                        'objects':[
                            {
                                'type':'KBaseSets.ReadsSet',
                                'data':readsSet_obj,
                                'name':name,
                                'meta':{},
                                'provenance':[
                                    {
                                        'service':'kb_ea_utils',
                                        'method':'test_run_ea-utils'
                                    }
                                ]
                            }]
                        })[0]

        # store it
        self.__class__.singleEndLib_SetInfo = new_obj_info
        return new_obj_info


    # call this method to get the WS object info of a Paired End Library Set (will
    # upload the example data if this is the first time the method is called during tests)
    def getPairedEndLib_SetInfo(self, read_libs_basename_list, refresh=False):
        if hasattr(self.__class__, 'pairedEndLib_SetInfo'):
            try:
                info = self.__class__.pairedEndLib_SetInfo
                if info != None:
                    if refresh:
                        self.__class__.pairedEndLib_SetInfo[lib_i] = None
                    else:
                        return info
            except:
                pass

        # build items and save each PairedEndLib
        items = []
        for lib_i,read_lib_basename in enumerate (read_libs_basename_list):
            label    = read_lib_basename
            lib_info = self.getPairedEndLibInfo (read_lib_basename, lib_i)
            lib_ref  = str(lib_info[6])+'/'+str(lib_info[0])
            print ("LIB_REF["+str(lib_i)+"]: "+lib_ref+" "+read_lib_basename)  # DEBUG

            items.append({'ref': lib_ref,
                          'label': label
                          #'data_attachment': ,
                          #'info':
                         })

        # save readsset
        desc = 'test ReadsSet'
        readsSet_obj = { 'description': desc,
                         'items': items
                       }
        name = 'TEST_READSET'

        new_obj_info = self.wsClient.save_objects({
                        'workspace':self.getWsName(),
                        'objects':[
                            {
                                'type':'KBaseSets.ReadsSet',
                                'data':readsSet_obj,
                                'name':name,
                                'meta':{},
                                'provenance':[
                                    {
                                        'service':'kb_ea_utils',
                                        'method':'test_run_ea-utils'
                                    }
                                ]
                            }]
                        })[0]

        # store it
        self.__class__.pairedEndLib_SetInfo = new_obj_info
        return new_obj_info


    ##############
    # UNIT TESTS #
    ##############


    # NOTE: According to Python unittest naming rules test method names should start from 'test'.
    #
    # Prepare test objects in workspace if needed using 
    # self.getWsClient().save_objects({'workspace': self.getWsName(), 'objects': []})
    #
    # Run your method by
    # ret = self.getImpl().your_method(self.getContext(), parameters...)
    #
    # Check returned data with
    # self.assertEqual(ret[...], ...) or other unittest methods

        # Object Info Contents
        # 0 - obj_id objid
        # 1 - obj_name name
        # 2 - type_string type
        # 3 - timestamp save_date
        # 4 - int version
        # 5 - username saved_by
        # 6 - ws_id wsid
        # 7 - ws_name workspace
        # 8 - string chsum
        # 9 - int size
        # 10 - usermeta meta


    ### TESTS 0.1-0.4: get Fastq Stats
    #
    def test_get_fastq_ea_utils_stats(self):
        print ("\n\nRUNNING: test_get_fastq_ea_utils_stats()")
        print ("========================================\n\n")
        # figure out where the test data lives
        pe_lib_info = self.getPairedEndLibInfo('mxtes(t_un)it')  # test weird filename chars
        pprint(pe_lib_info)

        # run method
        params = {
            'workspace_name': pe_lib_info[7],
            'read_library_ref': str(pe_lib_info[6])+'/'+str(pe_lib_info[0])
        }
        ea_utils_stats_str = self.getImpl().get_fastq_ea_utils_stats(self.getContext(),params)
        print('EA_UTILS_STATS_str:')
        print(ea_utils_stats_str)


    def test_run_app_fastq_ea_utils_stats(self):
        print ("\n\nRUNNING: test_run_app_fastq_ea_utils_stats()")
        print ("============================================\n\n")
        # figure out where the test data lives
        pe_lib_info = self.getPairedEndLibInfo('mxtes(t_un)it')
        pprint(pe_lib_info)

        # run method
        params = {
            'workspace_name': pe_lib_info[7],
            'read_library_ref': str(pe_lib_info[6])+'/'+str(pe_lib_info[0])
        }
        report = self.getImpl().run_app_fastq_ea_utils_stats(self.getContext(),params)
        print('REPORT:')
        pprint(report)


    def test_get_ea_utils_stats(self):
        print ("\n\nRUNNING: test_get_ea_utils_stats()")
        print ("==================================\n\n")
        fastq_file = "data/mxtes(t_un)it.fwd.fq"
        params={'read_library_path': fastq_file}

        report = self.getImpl().get_ea_utils_stats(self.getContext(), params)
        print('REPORT:')
        pprint(report)

    def test_calculate_fastq_stats(self):
        print ("\n\nRUNNING: test_calculate_fastq_stats()")
        print ("=====================================\n\n")
        fastq_file = "data/mxtes(t_un)it.fwd.fq"
        params={'read_library_path': fastq_file}

        ea_stats = self.getImpl().calculate_fastq_stats(self.getContext(), params)
        total_bases = 18750
        self.assertEqual(ea_stats[0]['total_bases'], total_bases)


    ### TEST 1: run Fastq_Multx against paired end library in manual mode
    #
    def test_run_Fastq_Multx_PE_manual_mode(self):

        print ("\n\nRUNNING: test_run_Fastq_Multx_PE_manual_mode()")
        print ("==============================================\n\n")

        # figure out where the test data lives
        pe_lib_info = self.getPairedEndLibInfo('mxtes(t_un)it')
        pprint(pe_lib_info)

        #index_lane_lib_info = self.getPairedEndLibInfo('mxtest_index_lane_unit')
        #pprint(index_lane_lib_info)

        # run method
        output_name = 'output_demult_manual.PERS'

        index_mode = 'manual'
        index_info = "id\tseq\tstyle\nLB1\tATCACG\tTruSeq\nLB2\tCGATGT\tTruSeq\nLB3\tTTAGGC\tTruSeq"

        params = {
            'workspace_name': pe_lib_info[7],
            'input_reads_ref': str(pe_lib_info[6])+'/'+str(pe_lib_info[0]),
            'index_mode': index_mode,
            'desc': 'TEST',
            'output_reads_name': output_name,
            'index_info': index_info,
            #'input_index_ref': str(index_lane_lib_info[6])+'/'+str(index_lane_lib_info[0]),
            'barcode_options': {
                'use_header_barcode': 0,
                'trim_barcode': 1,
                'suggest_barcodes': 0
                },
            'force_edge_options': {
                'force_beg': 0,
                'force_end': 0
                },
            'dist_and_qual_params': {
                'mismatch_max': 1,
                'edit_dist_min': 2,
                'barcode_base_qual_score_min': 1
                },
        }

        result = self.getImpl().run_Fastq_Multx(self.getContext(),params)
        print('RESULT:')
        pprint(result)

        # check the output
        output_name = output_name
        info_list = self.wsClient.get_object_info([{'ref':pe_lib_info[7] + '/' + output_name}], 1)
        self.assertEqual(len(info_list),1)
        readsSet_info = info_list[0]
        self.assertEqual(readsSet_info[1],output_name)
        self.assertEqual(readsSet_info[2].split('-')[0],'KBaseSets.ReadsSet')


    ### TEST 2: run Fastq_Multx against paired end library in index-lane mode
    #
    def test_run_Fastq_Multx_PE_index_lane_mode(self):

        print ("\n\nRUNNING: test_run_Fastq_Multx_PE_index_lane_mode()")
        print ("==================================================\n\n")

        # figure out where the test data lives
        pe_lib_info = self.getPairedEndLibInfo('mxtes(t_un)it')
        pprint(pe_lib_info)

        index_lane_lib_info = self.getSingleEndLibInfo('mxtest_ind (ex)_lane_unit')
        pprint(index_lane_lib_info)

        # run method
        output_name = 'output_demult_indexlane.PERS'

        index_mode = 'index-lane'
        index_info = "id\tseq\tstyle\nLB1\tATCACG\tTruSeq\nLB2\tCGATGT\tTruSeq\nLB3\tTTAGGC\tTruSeq"

        params = {
            'workspace_name': pe_lib_info[7],
            'input_reads_ref': str(pe_lib_info[6])+'/'+str(pe_lib_info[0]),
            'index_mode': index_mode,
            'desc': 'TEST',
            'output_reads_name': output_name,
            'index_info': index_info,
            'input_index_ref': str(index_lane_lib_info[6])+'/'+str(index_lane_lib_info[0]),
            'barcode_options': {
                'use_header_barcode': 0,
                'trim_barcode': 1,
                'suggest_barcodes': 0
                },
            'force_edge_options': {
                'force_beg': 0,
                'force_end': 0
                },
            'dist_and_qual_params': {
                'mismatch_max': 1,
                'edit_dist_min': 2,
                'barcode_base_qual_score_min': 1
                },
        }

        result = self.getImpl().run_Fastq_Multx(self.getContext(),params)
        print('RESULT:')
        pprint(result)

        # check the output
        output_name = output_name
        info_list = self.wsClient.get_object_info([{'ref':pe_lib_info[7] + '/' + output_name}], 1)
        self.assertEqual(len(info_list),1)
        readsSet_info = info_list[0]
        self.assertEqual(readsSet_info[1],output_name)
        self.assertEqual(readsSet_info[2].split('-')[0],'KBaseSets.ReadsSet')


    ### TEST 3: run Fastq_Multx against paired end library in auto-detect mode
    #
    def test_run_Fastq_Multx_PE_autodetect_mode(self):

        print ("\n\nRUNNING: test_run_Fastq_Multx_PE_autodetect_mode()")
        print ("==================================================\n\n")

        # figure out where the test data lives
        pe_lib_info = self.getPairedEndLibInfo('mxtes(t_un)it')
        pprint(pe_lib_info)

        #index_lane_lib_info = self.getPairedEndLibInfo('mxtest_index_lane_unit')
        #pprint(index_lane_lib_info)

        # run method
        output_name = 'output_demult_autodetect.PERS'

        index_mode = 'auto-detect'
        #index_info = "id\tseq\tstyle\nLB1\tATCACG\tTruSeq\nLB2\tCGATGT\tTruSeq\nLB3\tTTAGGC\tTruSeq"

        params = {
            'workspace_name': pe_lib_info[7],
            'input_reads_ref': str(pe_lib_info[6])+'/'+str(pe_lib_info[0]),
            'index_mode': index_mode,
            'desc': 'TEST',
            'output_reads_name': output_name,
            #'index_info': index_info,
            #'input_index_ref': str(index_lane_lib_info[6])+'/'+str(index_lane_lib_info[0]),
            'barcode_options': {
                'use_header_barcode': 0,
                'trim_barcode': 1,
                'suggest_barcodes': 0
                },
            'force_edge_options': {
                'force_beg': 0,
                'force_end': 0
                },
            'dist_and_qual_params': {
                'mismatch_max': 1,
                'edit_dist_min': 2,
                'barcode_base_qual_score_min': 1
                },
        }

        result = self.getImpl().run_Fastq_Multx(self.getContext(),params)
        print('RESULT:')
        pprint(result)

        # check the output
        output_name = output_name
        info_list = self.wsClient.get_object_info([{'ref':pe_lib_info[7] + '/' + output_name}], 1)
        self.assertEqual(len(info_list),1)
        readsSet_info = info_list[0]
        self.assertEqual(readsSet_info[1],output_name)
        self.assertEqual(readsSet_info[2].split('-')[0],'KBaseSets.ReadsSet')


    ### Used by TEST 4 and TEST 5

    def run_Fastq_Multx_PE_autodetect_mode_barcode_header(self, interLeaved=False):

        # figure out where the test data lives
        if (interLeaved):
            pe_lib_info = self.getPairedEndInterleavedLibInfo('mx(t)est-header')
        else:
            pe_lib_info = self.getPairedEndLibInfo('mx(t)est-header')

        pprint(pe_lib_info)

        #index_lane_lib_info = self.getPairedEndLibInfo('mxtest_index_lane_unit')
        #pprint(index_lane_lib_info)

        # run method
        output_name = 'output_demult_autodetect_barcode_header.PERS'

        index_mode = 'auto-detect'
        #index_info = "id\tseq\tstyle\nLB1\tATCACG\tTruSeq\nLB2\tCGATGT\tTruSeq\nLB3\tTTAGGC\tTruSeq"

        params = {
            'workspace_name': pe_lib_info[7],
            'input_reads_ref': str(pe_lib_info[6])+'/'+str(pe_lib_info[0]),
            'index_mode': index_mode,
            'desc': 'TEST',
            'output_reads_name': output_name,
            #'index_info': index_info,
            #'input_index_ref': str(index_lane_lib_info[6])+'/'+str(index_lane_lib_info[0]),
            'barcode_options': {
                'use_header_barcode': 1,  # this is special
                'trim_barcode': 0,        # so's this
                'suggest_barcodes': 0
                },
            'force_edge_options': {
                'force_beg': 0,
                'force_end': 0
                },
            'dist_and_qual_params': {
                'mismatch_max': 1,
                'edit_dist_min': 2,
                'barcode_base_qual_score_min': 1
                },
        }

        result = self.getImpl().run_Fastq_Multx(self.getContext(),params)
        print('RESULT:')
        pprint(result)

        # check the output
        output_name = output_name
        info_list = self.wsClient.get_object_info([{'ref':pe_lib_info[7] + '/' + output_name}], 1)
        self.assertEqual(len(info_list),1)
        readsSet_info = info_list[0]
        self.assertEqual(readsSet_info[1],output_name)
        self.assertEqual(readsSet_info[2].split('-')[0],'KBaseSets.ReadsSet')


    ### TEST 4: run Fastq_Multx against paired end library in autodetect mode with barcodes in header
    #
    def test_run_Fastq_Multx_PE_autodetect_mode_barcode_header(self):

        print ("\n\nRUNNING: test_run_Fastq_Multx_PE_autodetect_mode_barcode_header()")
        print ("         Input Lib is paired")
        print ("=================================================================\n\n")

        self.run_Fastq_Multx_PE_autodetect_mode_barcode_header(False)


    ### TEST 5: run Fastq_Multx against interleaved paired end library in autodetect mode with barcodes in header
    #

    def test_run_Fastq_Multx_PE_IL_autodetect_mode_barcode_header(self):

        print ("\n\nRUNNING: test_run_Fastq_Multx_PE_autodetect_mode_barcode_header()")
        print ("         Input Lib is interleaved")
        print ("=================================================================\n\n")

        self.run_Fastq_Multx_PE_autodetect_mode_barcode_header(True)


    ### TEST 6: run Fastq_Join against paired end library
    #
    def test_run_Fastq_Join_PE_lib(self):

        print ("\n\nRUNNING: test_run_Fastq_Join_PE_lib()")
        print ("=====================================\n\n")

        # figure out where the test data lives
        pe_lib_info = self.getPairedEndLibInfo('te(st-[o]v)-a')
        pprint(pe_lib_info)

        # run method
        output_name = 'output_join.PE_lib'

        params = {
            'workspace_name': pe_lib_info[7],
            'input_reads_ref': str(pe_lib_info[6])+'/'+str(pe_lib_info[0]),
            'output_reads_name': output_name,
            'verbose': 0,
            'reverse_complement': 1,
            'max_perc_dist': 8,
            'min_base_overlap': 6
        }

        result = self.getImpl().run_Fastq_Join(self.getContext(),params)
        print('RESULT:')
        pprint(result)

        # check the output
        output_name = output_name+"_joined"
        info_list = self.wsClient.get_object_info([{'ref':pe_lib_info[7] + '/' + output_name}], 1)
        self.assertEqual(len(info_list),1)
        readsLib_info = info_list[0]
        self.assertEqual(readsLib_info[1],output_name)
        self.assertEqual(readsLib_info[2].split('-')[0],'KBaseFile.SingleEndLibrary')


    ### TEST 7: run Fastq_Join against paired end library reads set
    #
    def test_run_Fastq_Join_PE_readsSet(self):

        print ("\n\nRUNNING: test_run_Fastq_Join_PE_readsSet()")
        print ("==========================================\n\n")

        # figure out where the test data lives
        pe_lib_set_info = self.getPairedEndLib_SetInfo(['te(st-[o]v)-a','test-ov- (b)'])
        pprint(pe_lib_set_info)

        # run method
        output_name = 'output_join.PE_readsSet'

        params = {
            'workspace_name': pe_lib_set_info[7],
            'input_reads_ref': str(pe_lib_set_info[6])+'/'+str(pe_lib_set_info[0]),
            'output_reads_name': output_name,
            'verbose': 0,
            'reverse_complement': 1,
            'max_perc_dist': 8,
            'min_base_overlap': 6
        }

        result = self.getImpl().run_Fastq_Join(self.getContext(),params)
        print('RESULT:')
        pprint(result)

        # check the output
        output_name = output_name+"_joined"
        info_list = self.wsClient.get_object_info([{'ref':pe_lib_set_info[7] + '/' + output_name}], 1)
        self.assertEqual(len(info_list),1)
        readsSet_info = info_list[0]
        self.assertEqual(readsSet_info[1],output_name)
        self.assertEqual(readsSet_info[2].split('-')[0],'KBaseSets.ReadsSet')
