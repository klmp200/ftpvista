# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from threading import Timer

from sqlalchemy import *
from sqlalchemy.orm import mapper, sessionmaker

from utils import Servers
import nmap_scanner

def never_date():
    """Helper that returns a DateTime object pointing to Epoch.

    This value is used as 'Never'."""
    return datetime.fromtimestamp(0)

def build_tables(meta):
    ftpservers = Table(
        'ftpservers', meta,
        Column('id', Integer, primary_key=True),
        Column('ip', String(15), nullable=False, unique=True),

        Column('first_seen', DATETIME, nullable=False, default=datetime.now),
        Column('last_seen', DATETIME, nullable=False, default=datetime.now),
        Column('last_scanned', DATETIME, nullable=False, default=never_date),

        Column('nb_files', Integer, default=0),
        Column('files_size', Integer, default=0)
        )

    return ftpservers

class FTPServer (object):
    def __init__(self, ip_addr):
        self.ip = ip_addr

    def update_last_seen(self, time=datetime.now()):
        self.last_seen = time

    def update_last_scanned(self, time=datetime.now()):
        self.last_scanned = time

    def get_server_id(self):
        return self.id

    def get_ip_addr(self):
        return self.ip

    def get_last_seen(self):
        return self.last_seen

    def get_last_scanned(self):
        return self.last_scanned

    def get_nb_files(self):
        return self.nb_files

    def set_nb_files(self, nb_files):
        self.nb_files = nb_files

    def get_files_size(self):
        return self.files_size

    def set_files_size(self, files_size):
        self.files_size = files_size
    
    def get_ip_with_name(self):
        return Servers.get_ip_with_name(self.ip)
    
    

class FTPVistaPersist(object):
    def __init__(self, db_uri):
        self.engine = create_engine(db_uri)
        self.meta = MetaData(self.engine)

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.servers = build_tables(self.meta)
        
        try:
            mapper(FTPServer, self.servers)
        except ArgumentError:
            pass

    def initialize_store(self):
        self.meta.create_all()

    def get_server_by_ip(self, ip_addr):
        server = self.session.query(FTPServer).filter_by(ip=ip_addr).first()

        if server == None:
            server = FTPServer(ip_addr)
            self.session.add(server)
            self.session.commit()

        return server

    def get_server(self, server_id):
        server = self.session.query(FTPServer).filter_by(id=server_id).first()
        return server

    def get_servers(self):
        return self.session.query(FTPServer).all()
    
    def launch_online_checker(self):
        self.log = logging.getLogger('online_check.nmaps')
        self._scanner = nmap_scanner.FTPFilter()
        """Timer launched every 5 minutes to check if servers in database are online"""
        self.check()
        Timer(60 * 5, self.check).start()
    
    def check(self):
        servers = self.get_servers()
        for server in servers:
            if self._scanner.is_ftp_open(server.get_ip_addr()):
                server.update_last_seen()
                self.log.info('Server %s is online. Last seen value updated to now !' % server.get_ip_addr())
        self.save()
        self.log.info('Online information saved !')

    def save(self):
        self.session.commit()