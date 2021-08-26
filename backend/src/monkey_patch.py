from gevent import monkey
import grpc.experimental.gevent as grpc_gevent

monkey.patch_all()
grpc_gevent.init_gevent()
