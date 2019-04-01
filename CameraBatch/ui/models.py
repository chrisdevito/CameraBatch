import logging
from maya import (cmds, OpenMaya)

log = logging.getLogger("CameraBatch")


class Camera(object):
    """
    Maya Camera object.
    """
    def __init__(self, camera="perspShape"):

        if cmds.nodeType(camera) == "transform":
            self.transform = camera
            self.shape = self.getShape(camera)

        elif cmds.nodeType(camera) == "camera":
            self.shape = camera
            self.transform = cmds.listRelatives(camera, parent=True)[0]

        else:
            log.error("%s is not a camera" % camera)
            raise RuntimeError("%s is not a camera" % camera)

        self.add_start_attr()
        self.add_end_attr()

    def __repr__(self):
        return "<%s instance of %s>" % (self.__class__.__name__, self.shape)

    def __mobject__(self):

        msel = OpenMaya.MSelectionList()
        msel.add(self.transform, 0)

        mobject = OpenMaya.MObject()
        msel.getDependNode(0, mobject)

        return mobject

    def getShape(self, transform):

        try:
            shape = cmds.listRelatives(
                transform, children=True, type="camera")[0]

            return shape

        except Exception:
            log.error("%s is not a camera" % transform)
            raise RuntimeError("%s is not a camera" % transform)

    @property
    def name(self):
        return self.transform

    @name.setter
    def name(self, value):
        self.transform = value
        self.shape = self.getShape(value)

    @property
    def focal_length(self):
        return cmds.getAttr(self.name + ".focalLength")

    @property
    def filmback(self):
        return [cmds.getAttr(self.name + ".horizontalFilmAperture"),
                cmds.getAttr(self.name + ".verticalFilmAperture")]

    @property
    def translation(self):
        return cmds.xform(
            self.transform, query=True, worldSpace=True, translation=True)

    @property
    def rotation(self):
        return cmds.xform(
            self.transform, query=True, worldSpace=True, rotation=True)

    def add_start_attr(self):

        if not cmds.objExists("{0}.start_frame".format(self.transform)):
            cmds.addAttr(
                self.transform,
                longName="start_frame",
                attributeType="long",
                defaultValue=1)
            cmds.setAttr(
                "{0}.start_frame".format(self.transform),
                edit=True,
                channelBox=True)
            self.start_frame = 1
        else:
            self.start_frame = cmds.getAttr(
                "{0}.start_frame".format(self.transform))

    def add_end_attr(self):

        if not cmds.objExists("{0}.end_frame".format(self.transform)):
            cmds.addAttr(
                self.transform,
                longName="end_frame",
                attributeType="long",
                defaultValue=10)
            cmds.setAttr(
                "{0}.end_frame".format(self.transform),
                edit=True,
                channelBox=True)
            self.end_frame = 10
        else:
            self.end_frame = cmds.getAttr(
                "{0}.end_frame".format(self.transform))
