from libs.channel import Channel

__author__ = 'DarkSupremo'

from libs.binary import BinaryStream

UNKNOWN = Channel()
UNKNOWN.id = -1
UNKNOWN.RGBA_Override = ''
UNKNOWN.name = 'UNKNOWN'

class PacketCHAN:
    def __bytes_to_hex(self, bytes):
        return "".join("{0:02x}".format(c) for c in bytes)

    def __init__(self, stream, channels):
        """
        @type stream: BinaryStream
        """
        self.length = stream.readInt16()
        for index in range(self.length):
            channel = Channel()
            channel.id = stream.readInt32()
            channel.unknown1 = stream.readInt32()
            channel.unknown2 = stream.readInt32()
            channel.verbosity_default = stream.readInt32()
            channel.verbosity_current = stream.readInt32()

            R = stream.readByte()
            G = stream.readByte()
            B = stream.readByte()
            A = stream.readByte()

            channel.RGBA_Override = self.__bytes_to_hex(R+G+B)


            channel.name = stream.readBytesNullTerminated(34)
            channels.append(channel)

    def channelById(self, channel_id, channels):
        """
        :return: Channel
        """
        for channel in channels:
            if channel.id == channel_id:
                return channel
        return UNKNOWN