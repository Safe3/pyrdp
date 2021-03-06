#
# This file is part of the PyRDP project.
# Copyright (C) 2018 GoSecure Inc.
# Licensed under the GPLv3 or later.
#

from collections import namedtuple

from pyrdp.core import ObservedBy, Uint8
from pyrdp.enum import SegmentationPDUType
from pyrdp.layer.buffered import BufferedLayer
from pyrdp.layer.layer import Layer, LayerObserver


class SegmentationObserver(LayerObserver):
    def onUnknownHeader(self, header):
        pass



SegmentationProxy = namedtuple("SegmentationProxy", "send")



@ObservedBy(SegmentationObserver)
class SegmentationLayer(Layer):
    """
    Layer to handle segmentation PDUs (e.g: TPKT and fast-path).
    Sends data to the proper BufferedLayer by checking the PDU's header.
    """

    def __init__(self):
        Layer.__init__(self)
        self.fastPathLayer = None
        self.layers = {}

    def attachLayer(self, type, layer):
        """
        Set the layer used for a type of segmentation PDU.
        :param type: the PDU type.
        :type type: int
        :param layer: the layer to use.
        :type layer: BufferedLayer
        """
        # The segmentation layer is bypassed when sending data.
        layer.previous = self.previous
        self.layers[type] = layer

    def recv(self, data):
        """
        Forward data to the proper layer depending on the PDU type.qq
        :type data: bytes
        """

        while len(data) > 0:
            layer = None
            length = 0

            # Check if any layer still needs to receive more data.
            for _, layer in self.layers.items():
                length = layer.getDataLengthRequired()

                if length > 0:
                    break

            if length == 0:
                # All layers are clear, this is a new PDU.
                # The PDU type is contained within the first byte of every message.
                header = Uint8.unpack(data[0]) & SegmentationPDUType.MASK

                try:
                    layer = self.layers[header]
                except KeyError:
                    if self.observer:
                        self.observer.onUnknownHeader(header)
                        return
                    else:
                        raise

                layer.recv(data[0 : 1])
                data = data[1 :]
                length = layer.getDataLengthRequired()

            # Send data to the selected layer as long as it needs some and as long as we have data to send.
            while length > 0 and len(data) > 0:
                forwarded = data[: length]
                data = data[length :]
                layer.recv(forwarded)
                length = layer.getDataLengthRequired()
