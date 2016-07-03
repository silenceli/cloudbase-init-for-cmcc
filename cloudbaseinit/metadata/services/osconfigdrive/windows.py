# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ctypes
import os
import shutil
import sys
import tempfile
import uuid
import traceback

from ctypes import wintypes
from oslo.config import cfg

from cloudbaseinit import exception
from cloudbaseinit.metadata.services.osconfigdrive import base
from cloudbaseinit.openstack.common import log as logging
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.utils.windows import physical_disk

opts = [
    cfg.StrOpt('bsdtar_path', default='bsdtar.exe',
               help='Path to "bsdtar", used to extract ISO ConfigDrive '
                    'files'),
]

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = logging.getLogger(__name__)


class WindowsConfigDriveManager(base.BaseConfigDriveManager):

    def _get_config_drive_cdrom_mount_point(self):
        osutils = osutils_factory.get_os_utils()

        for drive in osutils.get_cdrom_drives():
            label = osutils.get_volume_label(drive)
            if label == "config-2" and \
                os.path.exists(os.path.join(drive,
                                            'openstack\\latest\\'
                                            'meta_data.json')):
                return drive
        return None

    def _c_char_array_to_c_ushort(self, buf, offset):
        low = ctypes.cast(buf[offset],
                          ctypes.POINTER(wintypes.WORD)).contents
        high = ctypes.cast(buf[offset + 1],
                           ctypes.POINTER(wintypes.WORD)).contents
        return (high.value << 8) + low.value
    
    def _c_char_array_to_c_byte(self, buf, offset):
        data = ctypes.cast(buf[offset],
                          ctypes.POINTER(wintypes.BYTE)).contents
        return data.value

    def _c_char_array_to_c_uint(self, buf, offset):
        low = ctypes.cast(buf[offset],
                          ctypes.POINTER(wintypes.WORD)).contents
        middle = ctypes.cast(buf[offset + 1],
                           ctypes.POINTER(wintypes.WORD)).contents
        high = ctypes.cast(buf[offset + 2],
                           ctypes.POINTER(wintypes.WORD)).contents
        max = ctypes.cast(buf[offset + 3],
                           ctypes.POINTER(wintypes.WORD)).contents
        return (max.value << 24) + (high.value << 16) + (middle.value << 8) + low.value

    def _get_iso_disk_size(self, phys_disk):
        geom = phys_disk.get_geometry()

        if geom.MediaType != physical_disk.Win32_DiskGeometry.FixedMedia:
            return None

        disk_size = geom.Cylinders * geom.TracksPerCylinder * \
            geom.SectorsPerTrack * geom.BytesPerSector

        boot_record_off = 0x8000
        id_off = 1
        volume_size_off = 80
        block_size_off = 128
        iso_id = 'CD001'

        offset = boot_record_off / geom.BytesPerSector * geom.BytesPerSector
        bytes_to_read = geom.BytesPerSector

        if disk_size <= offset + bytes_to_read:
            return None

        phys_disk.seek(offset)
        (buf, bytes_read) = phys_disk.read(bytes_to_read)

        buf_off = boot_record_off - offset + id_off
        if iso_id != buf[buf_off: buf_off + len(iso_id)]:
            return None

        buf_off = boot_record_off - offset + volume_size_off
        num_blocks = self._c_char_array_to_c_ushort(buf, buf_off)

        buf_off = boot_record_off - offset + block_size_off
        block_size = self._c_char_array_to_c_ushort(buf, buf_off)

        return num_blocks * block_size

    def _write_iso_file(self, phys_disk, path, iso_file_size):
        with open(path, 'wb') as f:
            geom = phys_disk.get_geometry()
            offset = 0
            # Get a multiple of the sector byte size
            bytes_to_read = 4096 / geom.BytesPerSector * geom.BytesPerSector

            while offset < iso_file_size:
                phys_disk.seek(offset)
                bytes_to_read = min(bytes_to_read, iso_file_size - offset)
                (buf, bytes_read) = phys_disk.read(bytes_to_read)
                f.write(buf)
                offset += bytes_read

    def _extract_iso_files(self, osutils, iso_file_path, target_path):
        os.makedirs(target_path)

        args = [CONF.bsdtar_path, '-xf', iso_file_path, '-C', target_path]
        (out, err, exit_code) = osutils.execute_process(args, False)

        if exit_code:
            raise exception.CloudbaseInitException(
                'Failed to execute "bsdtar" from path "%(bsdtar_path)s" with '
                'exit code: %(exit_code)s\n%(out)s\n%(err)s' % {
                    'bsdtar_path': CONF.bsdtar_path,
                    'exit_code': exit_code,
                    'out': out, 'err': err})

    def _extract_iso_disk_file(self, osutils, iso_file_path):
        iso_disk_found = False
        for path in osutils.get_physical_disks():
            phys_disk = physical_disk.PhysicalDisk(path)
            try:
                phys_disk.open()
                iso_file_size = self._get_iso_disk_size(phys_disk)
                if iso_file_size:
                    LOG.debug('ISO9660 disk found on raw HDD: %s' % path)
                    self._write_iso_file(phys_disk, iso_file_path,
                                         iso_file_size)
                    iso_disk_found = True
                    break
            except Exception:
                # Ignore exception
                pass
            finally:
                phys_disk.close()
        return iso_disk_found

    def get_config_drive_files(self, target_path, check_raw_hhd=True,
                               check_cdrom=True):
        config_drive_found = False
        if check_raw_hhd:
            LOG.debug('Looking for Config Drive in raw HDDs')
            config_drive_found = self._get_conf_drive_from_raw_hdd(
                target_path)

        if not config_drive_found:
            LOG.debug('Looking for Config Drive in vfat')
            vfm = VfatManager()
            config_drive_found = vfm.is_found_vfat_configdrive()
            if config_drive_found:
                vfm.read_dir()
                vfm.mkdir_all(target_path)
            	del vfm

        if not config_drive_found and check_cdrom:
            LOG.debug('Looking for Config Drive in cdrom drives')
            config_drive_found = self._get_conf_drive_from_cdrom_drive(
                target_path)
        return config_drive_found

    def _get_conf_drive_from_cdrom_drive(self, target_path):
        cdrom_mount_point = self._get_config_drive_cdrom_mount_point()
        if cdrom_mount_point:
            shutil.copytree(cdrom_mount_point, target_path)
            return True
        return False

    def _get_conf_drive_from_raw_hdd(self, target_path):
        config_drive_found = False
        iso_file_path = os.path.join(tempfile.gettempdir(),
                                     str(uuid.uuid4()) + '.iso')
        try:
            osutils = osutils_factory.get_os_utils()

            if self._extract_iso_disk_file(osutils, iso_file_path):
                self._extract_iso_files(osutils, iso_file_path, target_path)
                config_drive_found = True
        finally:
            if os.path.exists(iso_file_path):
                os.remove(iso_file_path)
        return config_drive_found


class VfatManager(WindowsConfigDriveManager):
    # bfs = BYTE For Sector
    # rs  = Reserverd Sector
    # re  = Root Entries
    # spf = Sectors Per FAT
    # spc = Sectors Per Cluster
    # nof = Number of FAT
    # fst_string = File System Type
    # vl_string = Volume Label
    bfs = 0
    rs = 0
    re = 0
    spf = 0
    spc = 0
    nof = 0
    fst_string = ""
    vl_label = ""

    # fg:0x800    2048
    fattable1_pos = 0
    # fg:0x20800  133120
    root_dir_pos = 0
    # fg:0x24800   149504
    data_start_pos = 0
    # fg: 0x800     2048
    cluster_size = 0
    cluster_start = 2
    phys_disk = 0
    # config drive dir
    cd_dir = []
    found = 0

    def __init__(self):
        try:
            osutils = osutils_factory.get_os_utils()
            for path in osutils.get_physical_disks():
                temp_phys_disk = physical_disk.PhysicalDisk(path)
                try:
                    temp_phys_disk.open()
                    if self._is_vfat_configdrive(temp_phys_disk):
                        self.phys_disk = temp_phys_disk
                        self._read_vfat_mbr()
                        self.found = 1
                        LOG.debug('found vfat configdrive')
                        break
                    else:
                        temp_phys_disk.close()
                except Exception, e:
                    print e
                    print traceback.format_exc()
        except Exception, e:
            print e

    def _is_vfat_configdrive_found(self):
        if self.phys_disk == 0:
            return False
        else:
            return True

    def _is_vfat_configdrive(self, phys_disk):
        # read mbr
        offset = 0
        phys_disk.seek(offset)
        bytes_to_read = 512
        (buf, bytes_read) = phys_disk.read(bytes_to_read)
        fst_string = buf[0x36: 0x36 + 0x05]
        vl_label = buf[0x2B:0x2B + 0x08]

        if "FAT16" == fst_string:
            LOG.debug('vfat File System Type is %s' % fst_string)
            print 'vfat File System Type is %s' % fst_string
            if vl_label == "config-2" or vl_label == "CONFIG-2":
                print 'this is configdrive'
                LOG.debug('vfat configdrive volume label is %s, vl_label OK' % vl_label)
                return True
            else:
                LOG.debug('vfat configdrive volume label is %s, vl_label wrong' % vl_label)
                return False
        else:
            LOG.debug('File System Type is not vfat')
            print 'File System Type is not vfat'
            return False

    def _read_vfat_mbr(self):
        offset = 0
        self.phys_disk.seek(offset)
        bytes_to_read = 512
        (buf, bytes_read) = self.phys_disk.read(bytes_to_read)

        self.bfs = self._c_char_array_to_c_ushort(buf, 0x0B)
        self.rs = self._c_char_array_to_c_ushort(buf, 0x0E)
        self.re = self._c_char_array_to_c_ushort(buf, 0x11)
        self.spf = self._c_char_array_to_c_ushort(buf, 0x16)
        self.spc = self._c_char_array_to_c_byte(buf, 0x0D)
        self.nof = self._c_char_array_to_c_byte(buf, 0x10)
        self.fst_string = buf[0x36: 0x36 + 0x05]
        self.vl_label = buf[0x2B:0x2B + 0x08]

        # fg:0x800    2048
        self.fattable1_pos = self.rs * self.bfs
        # fg:0x20800  133120
        self.root_dir_pos = self.fattable1_pos + self.spf * self.bfs * self.nof
        # fg:0x24800   149504
        self.data_start_pos = self.root_dir_pos +  32 * self.re
        # fg:0x800     2048
        self.cluster_size = self.bfs * self.spc
        self.cluster_start = 2

    def _get_next_cluster_id_from_fattable(self, cluster_id):
        inside_offset = (cluster_id * 2) % self.cluster_size
        outside_offset = cluster_id / (self.cluster_size / 2) * self.cluster_size

        offset = outside_offset + self.fattable1_pos
        self.phys_disk.seek(offset)
        bytes_to_read = self.cluster_size
        (buf, bytes_read) = self.phys_disk.read(bytes_to_read)
        next_id = self._c_char_array_to_c_ushort(buf, inside_offset)

        # 0 is final cluster
        if next_id == 65535:
            return 0
        else:
            return next_id

    def _get_all_cluster_id_from_fattable(self, first_cluster_id):
        cluster_id_array = [first_cluster_id]
        number_of_cluster_id = 1
        next_id = self._get_next_cluster_id_from_fattable(first_cluster_id)

        while next_id != 0:
            cluster_id_array.append(next_id)
            print next_id
            next_id = self._get_next_cluster_id_from_fattable(next_id)
            number_of_cluster_id += 1

        #print "number_of_cluster_id = %d" % number_of_cluster_id
        #print "cluster_id_array = %s" % cluster_id_array
        return (cluster_id_array, number_of_cluster_id)

    def _get_cluster_data_from_cluster_id(self, cluster_id):
        offset = self.data_start_pos + (cluster_id - self.cluster_start) * self.cluster_size
        self.phys_disk.seek(offset)
        bytes_to_read = self.cluster_size
        (buf, bytes_read) = self.phys_disk.read(bytes_to_read)
        return buf

    def _get_all_cluster_data_from_first_cluster_id(self, first_cluster_id):
        buf = ""
        tempbuf = ""
        i = 0

        (cluster_id_array, number) = self._get_all_cluster_id_from_fattable(first_cluster_id)
        while i < number:
            tempbuf = self._get_cluster_data_from_cluster_id(cluster_id_array[i])
            try:
                buf += tempbuf.raw
            except Exception, e:
                print e
            i += 1
        return buf

    def _get_all_cluster_data_from_cluster_id_array(self, cluster_id_array):
        buf = ""
        tmpbuf = ""
        i = 0
        number = len(cluster_id_array)

        while i < number:
            tmpbuf = self._get_cluster_data_from_cluster_id(cluster_id_array[i])
            try:
                buf += tmpbuf.raw
            except Exception, e:
                print e
            i += 1

        return buf

    def _read_short_filename_entry(self, entry):
        is_dir = False
        flag = entry[0x0B]
        flag_num = ord(flag)
        i = 0
        filename = ""

        if flag_num & 16:
            is_dir = True
            size = -1
        else:
            size = self._c_char_array_to_c_uint(entry, 0x1C)

        first_cluster_id = self._c_char_array_to_c_ushort(entry, 0x1A)
        (cluster_id_array, number) = self._get_all_cluster_id_from_fattable(first_cluster_id)
        while i < 8 and entry[i] != '\x20':
            filename += entry[i]
            i += 1
        i = 0
        while i < 3 and entry[i+0x08] != '\x20':
            if i == 0:
                filename += "."
            filename += entry[i+0x08]
            i += 1

        return (is_dir, filename, cluster_id_array, size)

    def _read_long_filename_entry(self, buf, pos):
        i = 0
        j = 1
        filename = ""
        tmp_filename = ""
        entry = buf[pos*32:pos*32+32]
        flag = entry[0]
        flag_num = ord(flag)

        order = flag_num & 0b00011111
        is_final = flag_num & 64
        if is_final == 0:
            LOG.warn('first long file entry \'s is_final_flag should be 1, but now it is 0 ,it should not be happen')
            print "it should not happen"

        while i < order:
            while entry[j] != '\0' or entry[j+1] != '\0':
                num = self._c_char_array_to_c_ushort(entry, j)
                tmp_filename += chr(num)
                j += 2
                if j == 0x0B:
                    j = 0x0E
                elif j == 0x1A:
                    j = 0x1C
                elif j == 0x20:
                    break
            filename = tmp_filename + filename
            i += 1
            j = 1
            entry = buf[(pos+i)*32:(pos+i)*32+32]
            tmp_filename = ""

        return (filename, pos + order)

    # read_dir is to read the subdir
    def _read_dir_from_cluster_id(self, cluster_id, prefix_dir):
        i = 0

        if cluster_id == -1:
            offset = self.root_dir_pos
            self.phys_disk.seek(offset)
            bytes_to_read = 32 * self.re
            (buf, bytes_read) = self.phys_disk.read(bytes_to_read)
        else:
            buf = self._get_all_cluster_data_from_first_cluster_id(cluster_id)
        length = len(buf)
        entry = buf[0:32]
        cluster_id_array = []

        while entry[0] != '\0' and entry[1] != '\0' and i*32 < length:
            is_label = ord(entry[0x0B]) & 0b00001111
            if entry[0] == '\x2E':
                print "this is . or .. entry"
            elif entry[0] == '\xE5':
                print 'this entry is deleted'
            elif is_label == 0b00001000:
                print "this entry is volume label"
            else:
                if entry[0x0B] == '\x0F':
                    (long_filename, i) = self._read_long_filename_entry(buf, i)
                    entry = buf[i*32:i*32+32]
                    (dir_flag, filename, cluster_id_array, size) = self._read_short_filename_entry(entry)
                    filename = os.path.join(prefix_dir, long_filename)
                else:
                    (dir_flag, filename, cluster_id_array, size) = self._read_short_filename_entry(entry)
                    filename = os.path.join(prefix_dir, filename)

                self.cd_dir.append((dir_flag, filename, cluster_id_array, size))
                LOG.debug('entry: [is_dir,filename,cluster_id_array,size]=[%s,%s,%s,%d]' % (dir_flag, filename, cluster_id_array, size))
            i += 1
            entry = buf[i*32:i*32+32]

    def read_dir(self):
        self._read_dir_from_cluster_id(-1, "")
        i = 0

        while i < len(self.cd_dir):
            if self.cd_dir[i][0]:
                self._read_dir_from_cluster_id(self.cd_dir[i][2][0], self.cd_dir[i][1])
            i += 1

    def mkdir(self, is_dir, filename, cluster_id_array, size, prefix):
        path = os.path.join(prefix, filename)
        if is_dir:
            try:
                os.mkdir(path)
            except Exception, e:
                LOG.error(e)
                print e
        else:
            try:
                fp = open(path, 'wb')
            except Exception, e:
                LOG.error(e)
            if size < self.cluster_size * 16:
                buf = self._get_all_cluster_data_from_cluster_id_array(cluster_id_array)
                try:
                    fp.write(buf[0:size])
                except Exception, e:
                    LOG.error(e)
            else:
                i = 0
                num = len(cluster_id_array)

                while i < num:
                    buf = self._get_cluster_data_from_cluster_id(cluster_id_array[i])
                    if i == (num - 1):
                        try:
                            fp.write(buf[0:(num-1)*self.cluster_size-size])
                        except Exception, e:
                            LOG.error(e)
                    else:
                        try:
                            fp.write(buf[0:self.cluster_size])
                        except Exception, e:
                            LOG.error(e)
                    buf = ""
                    i += 1
            fp.close()

    def mkdir_all(self, prefix):
        num = len(self.cd_dir)
        i = 0
        os.mkdir(prefix)

        while i < num:
            self.mkdir(self.cd_dir[i][0], self.cd_dir[i][1], self.cd_dir[i][2], self.cd_dir[i][3], prefix)
            i += 1

    def is_found_vfat_configdrive(self):
        if self.found == 1:
            return True
        else:
            return False

    def __del__(self):
        self.phys_disk.close()
