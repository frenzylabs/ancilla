'''
 __init__.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/04/19
 Copyright 2019 Wess Cope
'''

from .printer   import PrinterResource
from .ports     import PortsResource
from .document  import DocumentResource
from .file      import FileResource
from .print     import PrintResource
from .camera    import CameraResource
from .webcam    import WebcamHandler
from .service    import ServiceResource
from .service_attachment import ServiceAttachmentResource
from .layerkeep    import LayerkeepResource


from .static  import StaticResource