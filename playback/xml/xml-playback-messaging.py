import sys, traceback, time
from seiscomp3 import Core, Client, DataModel, Communication, IO

class PickPlayer(Client.Application):

    def __init__(self, argc, argv):
        Client.Application.__init__(self, argc, argv)
        self.setMessagingEnabled(True)
        self.setDatabaseEnabled(False, False)
        self.setPrimaryMessagingGroup("PICK")
        self._startTime = self._endTime = None
        self._xmlFile = None
        self._send = True
        self.speed = 1

    def createCommandLineDescription(self):
        Client.Application.createCommandLineDescription(self)
        self.commandline().addGroup("Mode");
        self.commandline().addOption("Mode", "test", "Do not send any object");
        self.commandline().addGroup("Dump")
        self.commandline().addStringOption("Dump", "begin", "specify start of time window")
        self.commandline().addStringOption("Dump", "end", "specify end of time window")
        self.commandline().addStringOption("Dump", "speed", "specify speed factor")
        self.commandline().addGroup("Input")
        self.commandline().addStringOption("Input", "xml", "specify xml file")

    def validateParameters(self):
        if not self.commandline().hasOption("test"):
            if not self.commandline().hasOption("host"):
                sys.stderr.write("must specify host name on command line!\n")
                return False
        return True

    def init(self):
        if not Client.Application.init(self):
            return False

        try:    start = self.commandline().optionString("begin")
        except: start = None

        try:    end = self.commandline().optionString("end")
        except: end = None

        try:    self._xmlFile = self.commandline().optionString("xml")
        except: pass

        try:
            self.speed = self.commandline().optionString("speed")
            if self.speed == "0":
                self.speed = None
            else:
                self.speed = float(self.speed)
        except: self.speed = 1

        if not self._xmlFile:
            sys.stderr.write("must specify xml file\n")
            return False

        if start:
            self._startTime = Core.Time.GMT()
            if self._startTime.fromString(start, "%F %T") == False:
                sys.stderr.write("Wrong 'begin' format\n")
                return False
        if end:
            self._endTime = Core.Time.GMT()
            if self._endTime.fromString(end, "%F %T") == False:
                sys.stderr.write("Wrong 'end' format\n")
                return False

        return True

    def _readEventParametersFromXML(self):
        ar = IO.XMLArchive()
        if ar.open(self._xmlFile) == False:
            raise IOError, self._xmlFile + ": unable to open"
        obj = ar.readObject()
        if obj is None:
            raise TypeError, self._xmlFile + ": invalid format"
        ep  = DataModel.EventParameters.Cast(obj)
        if ep is None:
            raise TypeError, self._xmlFile + ": no eventparameters found"
        return ep

    def run(self):
        ep = self._readEventParametersFromXML()

        # collect the objects
        objs = []
        while ep.pickCount() > 0:
            # FIXME: The cast hack forces the SC3 refcounter to be increased.
            pick = DataModel.Pick.Cast(ep.pick(0))
            ep.removePick(0)
            objs.append(pick)
        while ep.amplitudeCount() > 0:
            # FIXME: The cast hack forces the SC3 refcounter to be increased.
            ampl = DataModel.Amplitude.Cast(ep.amplitude(0))
            ep.removeAmplitude(0)
#           if ampl.type() not in ["mb", "snr"]:
#               continue
            objs.append(ampl)
        while ep.originCount() > 0:
            # FIXME: The cast hack forces the SC3 refcounter to be increased.
            origin = DataModel.Origin.Cast(ep.origin(0))
            ep.removeOrigin(0)
            objs.append(origin)
        del ep

        # DSU sort all objects by object creation time
        sortlist = []
        for obj in objs:
            # discard objects that have no creationInfo attribute
            try:    t = obj.creationInfo().creationTime()
            except: continue

            if self._startTime is not None and t < self._startTime:
                continue
            if self._endTime is not None and t > self._endTime:
                continue
            sortlist.append( (t,obj) )
        sortlist.sort()

        time_of_1st_object, obj = sortlist[0]
        time_of_playback_start = Core.Time.GMT()

        ep = DataModel.EventParameters()
        pickampl = {}

        # go through the sorted list of object and process them sequentially
        for t,obj in sortlist:
            if self.isExitRequested(): return

            if self.speed:
                t = time_of_playback_start + Core.TimeSpan(float(t - time_of_1st_object) / self.speed)
                while t > Core.Time.GMT():
                    time.sleep(0.1)

            if obj.ClassName() not in [ "Pick", "Amplitude", "Origin" ]:
                continue

            if self._send:
                DataModel.Notifier.Enable()
                ep.add(obj)
                msg = DataModel.Notifier.GetMessage()
                if self.commandline().hasOption("test"):
                    sys.stderr.write("Test mode - not sending %-10s %s\n" % (obj.ClassName(), obj.publicID()))
                else:
                    if self.connection().send(msg):
                        sys.stderr.write("Sent %s %s\n" % (obj.ClassName(), obj.publicID()))
                    else:
                        sys.stderr.write("Failed to send %-10s %s\n" % (obj.ClassName(), obj.publicID()))
                DataModel.Notifier.Disable()
                self.sync()

        return

app = PickPlayer(len(sys.argv), sys.argv)
sys.exit(app())
