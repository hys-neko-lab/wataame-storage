from api import storage_pb2
from api import storage_pb2_grpc
import libvirt
import string
import os

class Storage(storage_pb2_grpc.StorageServicer):
    hostname = None
    hostpath = None
    def __init__(self, hostname, hostpath):
        self.conn = libvirt.open('qemu:///system')
        self.hostname=hostname
        self.hostpath=hostpath

    def createPool(self, request, context):
        if self.conn == None:
            message = "conn failed."
            return storage_pb2.CreatePoolReply(message=message)

        # マウント先ディレクトリ作成
        mntdir='mnt/{}'.format(request.uuid)
        os.makedirs(mntdir, exist_ok=True)

        # XMLテンプレートを元にストレージプール定義を作成
        # NOTE: 現状hostnameとhostpathは未使用
        with open('templates/storagepool.xml') as f:
            t = string.Template(f.read())
        xmlcreate = t.substitute(
            name=request.name,
            uuid=request.uuid,
            hostname=self.hostname,
            hostpath=self.hostpath,
            cap=request.cap,
            alloc=request.alloc,
            mntpath=os.path.abspath(mntdir),
        )
        print(xmlcreate)

        # ストレージプールを定義、自動スタート設定
        pool = self.conn.storagePoolDefineXML(xmlcreate, 0)
        if pool == None:
            message = "create storage pool failed"
            return storage_pb2.CreatePoolReply(message=message)

        pool.setAutostart(1) # set True
        if pool.create() != 0:
            message = "start storage pool failed"
            return storage_pb2.CreatePoolReply(message=message)
        
        message = "UUID:" + request.uuid + " created."
        return storage_pb2.CreatePoolReply(message=message)

    def deletePool(self, request, context):
        if self.conn == None:
            message = "conn failed."
            return storage_pb2.DeletePoolReply(message=message)
        
        pool = self.conn.storagePoolLookupByUUIDString(request.uuid)
        if pool == None:
            message = "find storage pool failed."
            return storage_pb2.DeletePoolReply(message=message)
        
        if pool.destroy() != 0:
            message = "stop storage pool failed."
            return storage_pb2.DeletePoolReply(message=message)
        
        if pool.undefine() != 0:
            message = "delete pool failed."
            return storage_pb2.DeletePoolReply(message=message)
        
        # マウント先ディレクトリ削除
        mntdir='mnt/{}'.format(request.uuid)
        os.rmdir(mntdir)

        message = "UUID:" + request.uuid + " deleted."
        return storage_pb2.DeletePoolReply(message=message)

    def createVolume(self, request, context):
        if self.conn == None:
            message = "conn failed."
            return storage_pb2.CreateVolumeReply(message=message)

        # マウント先ディレクトリ
        mntdir='mnt/{}'.format(request.pooluuid)
        # リクエストで受け取った名前に拡張子を付加
        vname = request.name + '.img'
        path = os.path.abspath(mntdir)

        # XMLテンプレートを元にボリューム定義を作成
        with open('templates/volume.xml') as f:
            t = string.Template(f.read())
        xmlcreate = t.substitute(
            name=vname,
            cap=request.cap,
            alloc=request.alloc,
            path=path,
        )
        print(xmlcreate)

        # ストレージプールをUUIDで探してその配下にボリュームを作成
        pool = self.conn.storagePoolLookupByUUIDString(request.pooluuid)
        if pool == None:
            message = "find pool failed"
            return storage_pb2.CreateVolumeReply(message=message)

        volume = pool.createXML(xmlcreate, 0)
        if volume == None:
            message = "create volume failed"
            return storage_pb2.CreateVolumeReply(message=message)
        
        message = path + '/' + vname
        return storage_pb2.CreateVolumeReply(message=message)

    def deleteVolume(self, request, context):
        if self.conn == None:
            message = "conn failed."
            return storage_pb2.DeleteVolumeReply(message=message)
        
        # ボリュームをパスで探し出して物理/論理削除
        volume = self.conn.storageVolLookupByPath(request.path)
        if volume == None:
            message = "find volume failed."
            return storage_pb2.DeleteVolumeReply(message=message)
        
        if volume.wipe(0) != 0:
            message = "delete phisical volume failed."
            return storage_pb2.DeleteVolumeReply(message=message)
        
        if volume.delete(0) != 0:
            message = "delete logical volume failed."
            return storage_pb2.DeleteVolumeReply(message=message)

        message = "Volume deleted."
        return storage_pb2.DeleteVolumeReply(message=message)