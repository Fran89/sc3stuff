import sys, seiscomp3.Core, seiscomp3.Client, seiscomp3.DataModel

class StreamingApp(seiscomp3.Client.StreamApplication):
    def __init__(self, argc, argv):
        seiscomp3.Client.StreamApplication.__init__(self, argc, argv)
        self.setMessagingEnabled(True)
        self.addMessagingSubscription("PICK")
        self.setDatabaseEnabled(False, False)
        self.setLoggingToStdErr(True)
        self.setDaemonEnabled(False)
        self.setRecordStreamEnabled(True)

    def init(self):
        if not seiscomp3.Client.StreamApplication.init(self):
            return False
        stream = self.recordStream()
        stream.addStream("GE","MORC","", "HHZ")
        stream.addStream("GE","KARP","", "HHZ")
        stream.addStream("GE","GHAJ","", "HHZ")
        return True

    def handleRecord(self, rec):
        print rec.stationCode(), rec.startTime()
        return True

    def addObject(self, parentID, obj):
        pick = seiscomp3.DataModel.Pick.Cast(obj)
        if pick:
            print "new pick", pick.publicID()

    def updateObject(self, parentID, obj):
        pick = seiscomp3.DataModel.Pick.Cast(obj)
        if pick:
            print "updated pick", pick.publicID()

app = StreamingApp(len(sys.argv), sys.argv)
app()
