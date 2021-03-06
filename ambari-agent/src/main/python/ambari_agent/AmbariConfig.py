#!/usr/bin/env python

'''
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

import logging
import ConfigParser
import StringIO
import hostname
import ambari_simplejson as json
import os

from ambari_commons import OSConst
from ambari_commons.os_family_impl import OsFamilyFuncImpl, OsFamilyImpl
logger = logging.getLogger(__name__)

content = """

[server]
hostname=localhost
url_port=8440
secured_url_port=8441

[agent]
prefix={ps}tmp{ps}ambari-agent
tmp_dir={ps}tmp{ps}ambari-agent{ps}tmp
data_cleanup_interval=86400
data_cleanup_max_age=2592000
data_cleanup_max_size_MB = 100
ping_port=8670
cache_dir={ps}var{ps}lib{ps}ambari-agent{ps}cache
parallel_execution=0
system_resource_overrides={ps}etc{ps}resource_overrides

[services]

[python]
custom_actions_dir = {ps}var{ps}lib{ps}ambari-agent{ps}resources{ps}custom_actions


[network]
use_system_proxy_settings=true

[security]
keysdir={ps}tmp{ps}ambari-agent
server_crt=ca.crt
passphrase_env_var_name=AMBARI_PASSPHRASE

[heartbeat]
state_interval = 6
dirs={ps}etc{ps}hadoop,{ps}etc{ps}hadoop{ps}conf,{ps}var{ps}run{ps}hadoop,{ps}var{ps}log{ps}hadoop
log_lines_count=300
iddle_interval_min=1
iddle_interval_max=10


[logging]
log_command_executes = 0

""".format(ps=os.sep)


servicesToPidNames = {
  'GLUSTERFS' : 'glusterd.pid$',
  'NAMENODE': 'hadoop-{USER}-namenode.pid$',
  'SECONDARY_NAMENODE': 'hadoop-{USER}-secondarynamenode.pid$',
  'DATANODE': 'hadoop-{USER}-datanode.pid$',
  'JOBTRACKER': 'hadoop-{USER}-jobtracker.pid$',
  'TASKTRACKER': 'hadoop-{USER}-tasktracker.pid$',
  'RESOURCEMANAGER': 'yarn-{USER}-resourcemanager.pid$',
  'NODEMANAGER': 'yarn-{USER}-nodemanager.pid$',
  'HISTORYSERVER': 'mapred-{USER}-historyserver.pid$',
  'JOURNALNODE': 'hadoop-{USER}-journalnode.pid$',
  'ZKFC': 'hadoop-{USER}-zkfc.pid$',
  'OOZIE_SERVER': 'oozie.pid',
  'ZOOKEEPER_SERVER': 'zookeeper_server.pid',
  'FLUME_SERVER': 'flume-node.pid',
  'TEMPLETON_SERVER': 'templeton.pid',
  'HBASE_MASTER': 'hbase-{USER}-master.pid',
  'HBASE_REGIONSERVER': 'hbase-{USER}-regionserver.pid',
  'HCATALOG_SERVER': 'webhcat.pid',
  'KERBEROS_SERVER': 'kadmind.pid',
  'HIVE_SERVER': 'hive-server.pid',
  'HIVE_METASTORE': 'hive.pid',
  'HIVE_SERVER_INTERACTIVE' : 'hive-interactive.pid',
  'MYSQL_SERVER': 'mysqld.pid',
  'HUE_SERVER': '/var/run/hue/supervisor.pid',
  'WEBHCAT_SERVER': 'webhcat.pid',
}

#Each service, which's pid depends on user should provide user mapping
servicesToLinuxUser = {
  'NAMENODE': 'hdfs_user',
  'SECONDARY_NAMENODE': 'hdfs_user',
  'DATANODE': 'hdfs_user',
  'JOURNALNODE': 'hdfs_user',
  'ZKFC': 'hdfs_user',
  'JOBTRACKER': 'mapred_user',
  'TASKTRACKER': 'mapred_user',
  'RESOURCEMANAGER': 'yarn_user',
  'NODEMANAGER': 'yarn_user',
  'HISTORYSERVER': 'mapred_user',
  'HBASE_MASTER': 'hbase_user',
  'HBASE_REGIONSERVER': 'hbase_user',
}

pidPathVars = [
  {'var' : 'glusterfs_pid_dir_prefix',
   'defaultValue' : '/var/run'},
  {'var' : 'hadoop_pid_dir_prefix',
   'defaultValue' : '/var/run/hadoop'},
  {'var' : 'hadoop_pid_dir_prefix',
   'defaultValue' : '/var/run/hadoop'},
  {'var' : 'hbase_pid_dir',
   'defaultValue' : '/var/run/hbase'},
  {'var' : 'zk_pid_dir',
   'defaultValue' : '/var/run/zookeeper'},
  {'var' : 'oozie_pid_dir',
   'defaultValue' : '/var/run/oozie'},
  {'var' : 'hcat_pid_dir',
   'defaultValue' : '/var/run/webhcat'},
  {'var' : 'hive_pid_dir',
   'defaultValue' : '/var/run/hive'},
  {'var' : 'mysqld_pid_dir',
   'defaultValue' : '/var/run/mysqld'},
  {'var' : 'hcat_pid_dir',
   'defaultValue' : '/var/run/webhcat'},
  {'var' : 'yarn_pid_dir_prefix',
   'defaultValue' : '/var/run/hadoop-yarn'},
  {'var' : 'mapred_pid_dir_prefix',
   'defaultValue' : '/var/run/hadoop-mapreduce'},
]


class AmbariConfig:
  TWO_WAY_SSL_PROPERTY = "security.server.two_way_ssl"
  AMBARI_PROPERTIES_CATEGORY = 'agentConfig'
  SERVER_CONNECTION_INFO = "{0}/connection_info"
  CONNECTION_PROTOCOL = "https"

  # linux open-file limit
  ULIMIT_OPEN_FILES_KEY = 'ulimit.open.files'

  config = None
  net = None

  def __init__(self):
    global content
    self.config = ConfigParser.RawConfigParser()
    self.config.readfp(StringIO.StringIO(content))

  def get(self, section, value, default=None):
    try:
      return str(self.config.get(section, value)).strip()
    except ConfigParser.Error, err:
      if default != None:
        return default
      raise err

  def set(self, section, option, value):
    self.config.set(section, option, value)

  def add_section(self, section):
    self.config.add_section(section)

  def has_section(self, section):
    return self.config.has_section(section)

  def setConfig(self, customConfig):
    self.config = customConfig

  def getConfig(self):
    return self.config

  @classmethod
  def get_resolved_config(cls, home_dir=""):
    if hasattr(cls, "_conf_cache"):
      return getattr(cls, "_conf_cache")
    config = cls()
    configPath = os.path.abspath(cls.getConfigFile(home_dir))
    try:
      if os.path.exists(configPath):
        config.read(configPath)
      else:
        raise Exception("No config found at {0}, use default".format(configPath))

    except Exception, err:
      logger.warn(err)
    setattr(cls, "_conf_cache", config)
    return config

  @staticmethod
  @OsFamilyFuncImpl(OsFamilyImpl.DEFAULT)
  def getConfigFile(home_dir=""):
    """
    Get the configuration file path.
    :param home_dir: In production, will be "". When running multiple Agents per host, each agent will have a unique path.
    :return: Configuration file path.
    """
    if 'AMBARI_AGENT_CONF_DIR' in os.environ:
      return os.path.join(os.environ['AMBARI_AGENT_CONF_DIR'], "ambari-agent.ini")
    else:
      # home_dir may be an empty string
      return os.path.join(os.sep, home_dir, "etc", "ambari-agent", "conf", "ambari-agent.ini")

  # TODO AMBARI-18733, change usages of this function to provide the home_dir.
  @staticmethod
  def getLogFile(home_dir=""):
    """
    Get the log file path.
    :param home_dir: In production, will be "". When running multiple Agents per host, each agent will have a unique path.
    :return: Log file path.
    """
    if 'AMBARI_AGENT_LOG_DIR' in os.environ:
      return os.path.join(os.environ['AMBARI_AGENT_LOG_DIR'], "ambari-agent.log")
    else:
      return os.path.join(os.sep, home_dir, "var", "log", "ambari-agent", "ambari-agent.log")

  # TODO AMBARI-18733, change usages of this function to provide the home_dir.
  @staticmethod
  def getAlertsLogFile(home_dir=""):
    """
    Get the alerts log file path.
    :param home_dir: In production, will be "". When running multiple Agents per host, each agent will have a unique path.
    :return: Alerts log file path.
    """
    if 'AMBARI_AGENT_LOG_DIR' in os.environ:
      return os.path.join(os.environ['AMBARI_AGENT_LOG_DIR'], "ambari-agent.log")
    else:
      return os.path.join(os.sep, home_dir, "var", "log", "ambari-agent", "ambari-alerts.log")

  # TODO AMBARI-18733, change usages of this function to provide the home_dir.
  @staticmethod
  def getOutFile(home_dir=""):
    """
    Get the out file path.
    :param home_dir: In production, will be "". When running multiple Agents per host, each agent will have a unique path.
    :return: Out file path.
    """
    if 'AMBARI_AGENT_LOG_DIR' in os.environ:
      return os.path.join(os.environ['AMBARI_AGENT_LOG_DIR'], "ambari-agent.out")
    else:
      return os.path.join(os.sep, home_dir, "var", "log", "ambari-agent", "ambari-agent.out")

  def has_option(self, section, option):
    return self.config.has_option(section, option)

  def remove_option(self, section, option):
    return self.config.remove_option(section, option)

  def load(self, data):
    self.config = ConfigParser.RawConfigParser(data)

  def read(self, filename):
    self.config.read(filename)

  def getServerOption(self, url, name, default=None):
    from ambari_agent.NetUtil import NetUtil
    status, response = NetUtil(self).checkURL(url)
    if status is True:
      try:
        data = json.loads(response)
        if name in data:
          return data[name]
      except:
        pass
    return default

  def get_api_url(self, server_hostname):
    return "%s://%s:%s" % (self.CONNECTION_PROTOCOL,
                           server_hostname,
                           self.get('server', 'url_port'))

  def isTwoWaySSLConnection(self, server_hostname):
    req_url = self.get_api_url(server_hostname)
    response = self.getServerOption(self.SERVER_CONNECTION_INFO.format(req_url), self.TWO_WAY_SSL_PROPERTY, 'false')
    if response is None:
      return False
    elif response.lower() == "true":
      return True
    else:
      return False

  def get_parallel_exec_option(self):
    return int(self.get('agent', 'parallel_execution', 0))

  def get_ulimit_open_files(self):
    open_files_config_val =  int(self.get('agent', self.ULIMIT_OPEN_FILES_KEY, 0))
    open_files_ulimit = int(open_files_config_val) if (open_files_config_val and int(open_files_config_val) > 0) else 0
    return open_files_ulimit

  def set_ulimit_open_files(self, value):
    self.set('agent', self.ULIMIT_OPEN_FILES_KEY, value)


  def use_system_proxy_setting(self):
    """
    Return `True` if Agent need to honor system proxy setting and `False` if not

    :rtype bool
    """
    return "true" == self.get("network", "use_system_proxy_settings", "true").lower()

  def get_multiprocess_status_commands_executor_enabled(self):
    return bool(int(self.get('agent', 'multiprocess_status_commands_executor_enabled', 1)))

  def update_configuration_from_registration(self, reg_resp):
    if reg_resp and AmbariConfig.AMBARI_PROPERTIES_CATEGORY in reg_resp:
      if not self.has_section(AmbariConfig.AMBARI_PROPERTIES_CATEGORY):
        self.add_section(AmbariConfig.AMBARI_PROPERTIES_CATEGORY)
      for k,v in reg_resp[AmbariConfig.AMBARI_PROPERTIES_CATEGORY].items():
        self.set(AmbariConfig.AMBARI_PROPERTIES_CATEGORY, k, v)
        logger.info("Updating config property (%s) with value (%s)", k, v)
    pass

  def get_force_https_protocol(self):
    return self.get('security', 'force_https_protocol', default="PROTOCOL_TLSv1")

def isSameHostList(hostlist1, hostlist2):
  is_same = True

  if (hostlist1 is not None and hostlist2 is not None):
    if (len(hostlist1) != len(hostlist2)):
      is_same = False
    else:
      host_lookup = {}
      for item1 in hostlist1:
        host_lookup[item1.lower()] = True
      for item2 in hostlist2:
        if item2.lower() in host_lookup:
          del host_lookup[item2.lower()]
        else:
          is_same = False
          break
    pass
  elif (hostlist1 is not None or hostlist2 is not None):
    is_same = False
  return is_same

def updateConfigServerHostname(configFile, new_hosts):
  # update agent config file
  agent_config = ConfigParser.ConfigParser()
  agent_config.read(configFile)
  server_hosts = agent_config.get('server', 'hostname')
  if new_hosts is not None:
      new_host_names = hostname.arrayFromCsvString(new_hosts)
      if not isSameHostList(server_hosts, new_host_names):
        print "Updating server hostname from " + server_hosts + " to " + new_hosts
        agent_config.set('server', 'hostname', new_hosts)
        with (open(configFile, "wb")) as new_agent_config:
          agent_config.write(new_agent_config)

def main():
  print AmbariConfig().config

if __name__ == "__main__":
  main()
