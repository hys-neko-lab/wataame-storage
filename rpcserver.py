from concurrent import futures
import grpc
import sys
from api import storage_pb2_grpc
import storage

def run(hostname, hostpath):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    storage_pb2_grpc.add_StorageServicer_to_server(
        storage.Storage(hostname=hostname, hostpath=hostpath),
        server)
    server.add_insecure_port('[::]:8083')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    args = sys.argv
    run('127.0.0.1', '/dummy')