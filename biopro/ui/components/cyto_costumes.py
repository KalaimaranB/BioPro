import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from biopro.ui.components.cyto_character import CytoWidget

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsRectItem,
)

from biopro.shared.ui.effects import apply_glow_effect


class CytoCostume:
    """Base interface for Cyto's theme-dependent accessories/costumes."""

    def attach(self, cyto_widget: "CytoWidget") -> None:
        pass

    def detach(self, cyto_widget: "CytoWidget") -> None:
        pass

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:
        pass


class GalacticCostume(CytoCostume):
    """Lightsaber costume; glow_color lets the factory pick a hue per Galactic variant.

    The blade itself stays a near-white core (real lightsabers read as
    white-hot at the center) — the variant's color comes through as a
    light-toned bloom around it, not a solid deep-saturated fill.
    """

    def __init__(self, glow_color: str = "#58a6ff", core_tint: str = "#eaf4ff"):
        self.items = []
        self.glow_effect = None
        self.glow_color = glow_color
        self.core_tint = core_tint

    def attach(self, cyto_widget: "CytoWidget") -> None:
        """
        Attach a handle and glowing blade accessory to the cyto widget's right arm.

        Parameters:
            cyto_widget: Widget whose right arm receives the accessory.
        """
        self.handle = QGraphicsRectItem(45, -20, 10, 35)
        handle_grad = QLinearGradient(45, -20, 55, -20)
        handle_grad.setColorAt(0, QColor("#8b949e"))
        handle_grad.setColorAt(1, QColor("#c9d1d9"))
        self.handle.setBrush(QBrush(handle_grad))
        self.handle.setPen(QPen(QColor("#ffffff"), 1))
        self.handle.setParentItem(cyto_widget.right_arm)
        self.items.append(self.handle)

        self.blade = QGraphicsRectItem(47, -100, 6, 80)
        self.blade.setBrush(QBrush(QColor(self.core_tint)))
        self.blade.setPen(QPen(Qt.PenStyle.NoPen))
        self.blade.setParentItem(cyto_widget.right_arm)
        self.items.append(self.blade)

        self.glow_effect = apply_glow_effect(self.blade, QColor(self.glow_color), blur_radius=22)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach and remove all costume items from the scene.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:  # noqa: ARG002
        """
        Updates the costume's glow intensity for the current animation time.

        Parameters:
            time_step (float): Current animation time used to vary the blur radius.
        """
        if self.glow_effect:
            hum_blur = 20 + math.sin(time_step * 15) * 6
            self.glow_effect.setBlurRadius(hum_blur)


class MandalorianCostume(CytoCostume):
    def __init__(self):
        self.items = []

    def attach(self, cyto_widget: "CytoWidget") -> None:
        # A Beskar chest plate rather than a full helmet — the previous
        # helmet (even tinted) still visually overwhelmed Cyto's own
        # identity. A shoulder-mounted pauldron was tried next, but never
        # read as properly attached to his rounded, shoulderless body;
        # worn center-chest instead (the same spot the kolam/DNA pendant
        # and Korra's necklace use successfully), it reads as armor worn
        # on him rather than a piece floating at his edge.
        self.chestplate = QGraphicsPathItem()
        cp_path = QPainterPath()
        cp_path.moveTo(-13, -14)
        cp_path.lineTo(13, -14)
        cp_path.lineTo(15, 0)
        cp_path.quadTo(13, 14, 0, 16)
        cp_path.quadTo(-13, 14, -15, 0)
        cp_path.closeSubpath()
        self.chestplate.setPath(cp_path)
        plate_grad = QLinearGradient(-13, -14, 13, 16)
        plate_grad.setColorAt(0, QColor("#f0f0f0"))
        plate_grad.setColorAt(0.5, QColor("#a8a8a8"))
        plate_grad.setColorAt(1, QColor("#5a5a5a"))
        self.chestplate.setBrush(QBrush(plate_grad))
        self.chestplate.setPen(QPen(QColor("#2b2b2b"), 1.3))
        self.chestplate.setParentItem(cyto_widget.cyto_group)
        self.chestplate.setPos(0, 34)
        self.chestplate.setZValue(2.6)
        self.items.append(self.chestplate)

        for rx, ry in [(-9, -9), (9, -9), (0, 11)]:
            rivet = QGraphicsEllipseItem(-1.3, -1.3, 2.6, 2.6)
            rivet.setBrush(QBrush(QColor("#333333")))
            rivet.setPen(QPen(Qt.PenStyle.NoPen))
            rivet.setParentItem(self.chestplate)
            rivet.setPos(rx, ry)

        # Mythosaur skull emblem centered on the plate — the actual
        # Mandalorian guild symbol, in Cyto's own blue so it still reads
        # as part of him rather than a foreign decal.
        self.signet = QGraphicsPathItem()
        sig_path = QPainterPath()
        sig_path.moveTo(0, -6)
        sig_path.cubicTo(-5, -6, -5.5, 1.5, -2.5, 4)
        sig_path.lineTo(-1.2, 6.5)
        sig_path.lineTo(0, 4.5)
        sig_path.lineTo(1.2, 6.5)
        sig_path.lineTo(2.5, 4)
        sig_path.cubicTo(5.5, 1.5, 5, -6, 0, -6)
        sig_path.closeSubpath()
        self.signet.setPath(sig_path)
        self.signet.setBrush(QBrush(QColor("#1f6feb")))
        self.signet.setPen(QPen(QColor("#79c0ff"), 1))
        self.signet.setParentItem(self.chestplate)
        self.items.append(self.signet)

        horn_pen = QPen(QColor("#79c0ff"), 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        for side in (-1, 1):
            horn = QGraphicsPathItem()
            h_path = QPainterPath()
            h_path.moveTo(side * 3, -5)
            h_path.quadTo(side * 7, -8, side * 5.5, -2.5)
            horn.setPath(h_path)
            horn.setPen(horn_pen)
            horn.setParentItem(self.signet)

        # Blaster pointing forward (horizontal) — kept close to the hand so
        # it reads as held, not floating off on its own.
        self.stock = QGraphicsPathItem()
        s_path = QPainterPath()
        s_path.moveTo(35, -5)
        s_path.lineTo(48, -5)
        s_path.lineTo(48, 5)
        s_path.lineTo(30, 5)
        s_path.closeSubpath()
        self.stock.setPath(s_path)

        tech_grad = QLinearGradient(30, -5, 48, 5)
        tech_grad.setColorAt(0, QColor("#1f6feb"))
        tech_grad.setColorAt(1, QColor("#010409"))
        self.stock.setBrush(QBrush(tech_grad))
        self.stock.setPen(QPen(QColor("#79c0ff"), 1.5))
        self.stock.setParentItem(cyto_widget.right_arm)
        self.items.append(self.stock)

        self.barrel = QGraphicsRectItem(48, -3, 30, 4)
        metal_grad = QLinearGradient(48, -3, 48, 1)
        metal_grad.setColorAt(0, QColor("#c9d1d9"))
        metal_grad.setColorAt(1, QColor("#484f58"))
        self.barrel.setBrush(QBrush(metal_grad))
        self.barrel.setParentItem(cyto_widget.right_arm)
        self.items.append(self.barrel)

        self.scope = QGraphicsRectItem(54, -8, 15, 3)
        self.scope.setBrush(QBrush(QColor("#161b22")))
        self.scope.setParentItem(cyto_widget.right_arm)
        self.items.append(self.scope)

        self.fork1 = QGraphicsRectItem(78, -6, 7, 2)
        self.fork1.setBrush(QBrush(metal_grad))
        self.fork1.setParentItem(cyto_widget.right_arm)
        self.items.append(self.fork1)

        self.fork2 = QGraphicsRectItem(78, 2, 7, 2)
        self.fork2.setBrush(QBrush(metal_grad))
        self.fork2.setParentItem(cyto_widget.right_arm)
        self.items.append(self.fork2)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach and remove all costume items from the scene.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()


class TriStateCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.hat_group = None
        self.lens_glow = None

    def attach(self, cyto_widget: "CytoWidget") -> None:
        """
        Attach the fedora and magnifying-glass accessories to the cyto widget.
        """
        self.hat_group = QGraphicsItemGroup()
        self.hat_group.setParentItem(cyto_widget.cyto_group)
        self.hat_group.setZValue(6)
        self.items.append(self.hat_group)

        self.brim = QGraphicsPathItem()
        b_path = QPainterPath()
        b_path.moveTo(-50, -42)
        b_path.quadTo(0, -55, 50, -42)
        b_path.quadTo(0, -47, -50, -42)
        self.brim.setPath(b_path)

        fedora_grad = QLinearGradient(-50, -80, 50, -40)
        fedora_grad.setColorAt(0, QColor(0, 168, 150, 230))
        fedora_grad.setColorAt(1, QColor(0, 80, 72, 230))

        self.brim.setBrush(QBrush(fedora_grad))
        self.brim.setPen(QPen(QColor("#00a896"), 2))
        self.brim.setParentItem(self.hat_group)

        self.crown = QGraphicsPathItem()
        c_path = QPainterPath()
        c_path.moveTo(-30, -50)
        c_path.lineTo(-25, -80)
        c_path.quadTo(0, -70, 25, -80)
        c_path.lineTo(30, -50)
        c_path.closeSubpath()
        self.crown.setPath(c_path)
        self.crown.setBrush(QBrush(fedora_grad))
        self.crown.setPen(QPen(QColor("#00a896"), 2))
        self.crown.setParentItem(self.hat_group)

        self.band = QGraphicsPathItem()
        band_path = QPainterPath()
        band_path.moveTo(-31, -48)
        band_path.lineTo(-28, -58)
        band_path.quadTo(0, -63, 28, -58)
        band_path.lineTo(31, -48)
        band_path.quadTo(0, -53, -31, -48)
        self.band.setPath(band_path)
        self.band.setBrush(QBrush(QColor("#010409")))
        self.band.setParentItem(self.hat_group)

        self.buckle = QGraphicsRectItem(-5, -60, 10, 8)
        self.buckle.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.buckle.setPen(QPen(QColor("#ffcc00"), 2))
        self.buckle.setParentItem(self.hat_group)

        hat_glow = apply_glow_effect(self.hat_group, QColor("#111111"), blur_radius=15)
        hat_glow.setOffset(0, 0)
        self.crown.setGraphicsEffect(hat_glow)

        # Detective's magnifying glass — pairs with the fedora and still
        # works as Cyto's UI pointer. Drawn as an angled rod running up to
        # a glass-tinted lens, sized and positioned close to the hand so it
        # reads as held rather than floating beside the arm.
        self.handle = QGraphicsPathItem()
        h_path = QPainterPath()
        h_path.moveTo(38, 8)
        h_path.lineTo(45, 14)
        h_path.lineTo(73, -27)
        h_path.lineTo(66, -33)
        h_path.closeSubpath()
        self.handle.setPath(h_path)
        handle_grad = QLinearGradient(38, 8, 73, -27)
        handle_grad.setColorAt(0, QColor("#5c3a21"))
        handle_grad.setColorAt(1, QColor("#8b5a2b"))
        self.handle.setBrush(QBrush(handle_grad))
        self.handle.setPen(QPen(QColor("#3d2615"), 1))
        self.handle.setParentItem(cyto_widget.right_arm)
        self.items.append(self.handle)

        self.lens = QGraphicsEllipseItem(55, -59, 34, 34)
        lens_grad = QRadialGradient(72, -42, 20)
        lens_grad.setColorAt(0, QColor(255, 255, 255, 180))
        lens_grad.setColorAt(0.55, QColor(190, 235, 230, 100))
        lens_grad.setColorAt(1, QColor(0, 168, 150, 60))
        self.lens.setBrush(QBrush(lens_grad))
        self.lens.setPen(QPen(QColor("#00a896"), 3))
        self.lens.setParentItem(cyto_widget.right_arm)
        self.items.append(self.lens)

        self.rim_screw = QGraphicsEllipseItem(69, -32, 5, 5)
        self.rim_screw.setBrush(QBrush(QColor("#ffcc00")))
        self.rim_screw.setPen(QPen(QColor("#3d2615"), 1))
        self.rim_screw.setParentItem(cyto_widget.right_arm)
        self.items.append(self.rim_screw)

        self.lens_glow = apply_glow_effect(self.lens, QColor("#ff0000"), blur_radius=15)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach and remove all costume items from the scene.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:  # noqa: ARG002
        """
        Animate the hat rotation and magnifying-glass lens glow.

        Parameters:
            time_step (float): Elapsed time used to calculate animation values.
        """
        if self.hat_group:
            angle = math.sin(time_step) * 5
            self.hat_group.setRotation(angle)
        if self.lens_glow:
            self.lens_glow.setBlurRadius(12 + math.sin(time_step * 3) * 4)


class SubcavernCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.glow_effect = None
        self.crystals = []

    def attach(self, cyto_widget: "CytoWidget") -> None:
        # Blaster pointing forward (horizontal)
        """
        Attach a blaster-like accessory with a glowing chamber to the cyto widget's right arm.

        Parameters:
            cyto_widget: Widget whose right arm receives the accessory items.
        """
        self.body = QGraphicsPathItem()
        b_path = QPainterPath()
        b_path.moveTo(35, -8)
        b_path.lineTo(65, -8)
        b_path.lineTo(65, 8)
        b_path.lineTo(40, 8)
        b_path.lineTo(35, 3)
        b_path.closeSubpath()
        self.body.setPath(b_path)

        grad = QLinearGradient(35, -8, 65, 8)
        grad.setColorAt(0, QColor("#e0e0e0"))
        grad.setColorAt(1, QColor("#666666"))
        self.body.setBrush(QBrush(grad))
        self.body.setPen(QPen(QColor("#333333"), 1.5))
        self.body.setParentItem(cyto_widget.right_arm)
        self.items.append(self.body)

        self.barrel = QGraphicsRectItem(65, -3, 20, 6)
        b_grad = QLinearGradient(65, -3, 65, 3)
        b_grad.setColorAt(0, QColor("#ffaa00"))
        b_grad.setColorAt(1, QColor("#cc5500"))
        self.barrel.setBrush(QBrush(b_grad))
        self.barrel.setParentItem(cyto_widget.right_arm)
        self.items.append(self.barrel)

        self.chamber = QGraphicsEllipseItem(46, -6, 12, 12)
        c_grad = QRadialGradient(52, 0, 6)
        c_grad.setColorAt(0, QColor(0, 255, 255, 150))
        c_grad.setColorAt(1, QColor(0, 100, 200, 200))
        self.chamber.setBrush(QBrush(c_grad))
        self.chamber.setPen(QPen(QColor("#00ffff"), 1))
        self.chamber.setParentItem(cyto_widget.right_arm)
        self.items.append(self.chamber)

        # The "slug" ammo — previously a stray lens-shaped sliver that
        # didn't read as anything in particular. A clear oval creature
        # body with two small eye-dots, centered inside the chamber
        # (rather than overlapping its edge), so it reads unambiguously
        # as a slug loaded in the glass rather than a part sticking out.
        self.slug = QGraphicsEllipseItem(-4, -2.5, 8, 5)
        self.slug.setBrush(QBrush(QColor("#ff8800")))
        self.slug.setPen(QPen(QColor("#cc5500"), 0.5))
        self.slug.setPos(52, 0)
        self.slug.setParentItem(cyto_widget.right_arm)
        self.slug.setZValue(1)
        self.items.append(self.slug)

        for ex in (-2, 2):
            eye = QGraphicsEllipseItem(-0.6, -0.6, 1.2, 1.2)
            eye.setBrush(QBrush(QColor("#3a1a00")))
            eye.setPen(QPen(Qt.PenStyle.NoPen))
            eye.setParentItem(self.slug)
            eye.setPos(ex, -1)

        self.glow_effect = apply_glow_effect(self.chamber, QColor(0, 255, 255), blur_radius=15)

        # Luminous cavern crystals — small radiant shards on the shoulder
        # that stand in for the "Luminous" half of the theme (the slug
        # blaster above covers Slugterra's iconic weapon).
        self.crystals = []
        crystal_specs = [
            ((-38, -30), 10, QColor(0, 230, 255)),
            ((-30, -42), 8, QColor(170, 90, 255)),
            ((-44, -18), 7, QColor(0, 230, 255)),
        ]
        for (cx, cy), size, color in crystal_specs:
            crystal = QGraphicsPathItem()
            c_path = QPainterPath()
            c_path.moveTo(0, -size)
            c_path.lineTo(size * 0.5, 0)
            c_path.lineTo(0, size)
            c_path.lineTo(-size * 0.5, 0)
            c_path.closeSubpath()
            crystal.setPath(c_path)
            crystal.setPos(cx, cy)
            crystal.setBrush(QBrush(color))
            crystal.setPen(QPen(color.lighter(150), 1))
            crystal.setParentItem(cyto_widget.cyto_group)
            crystal.setZValue(
                1.5
            )  # above the body (1) so it reads as an embedded shard, not hidden behind it
            apply_glow_effect(crystal, color, blur_radius=12)
            self.crystals.append(crystal)
            self.items.append(crystal)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach and remove all costume items from the scene.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()
        self.crystals.clear()

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:  # noqa: ARG002
        """
        Update the chamber glow intensity and crystal flicker for the current animation time.
        """
        if self.glow_effect:
            radius = 15 + math.sin(time_step * 8) * 5
            self.glow_effect.setBlurRadius(radius)
        # A slow, gentle shimmer rather than a fast flicker — the crystals
        # are meant to sit quietly in the scene, not draw the eye.
        for i, crystal in enumerate(self.crystals):
            shimmer = 0.85 + math.sin(time_step * 0.6 + i * 2.1) * 0.15
            crystal.setOpacity(shimmer)


class FamilyGuyCostume(CytoCostume):
    """Quahog Static theme — a Stewie bonnet plus a chicken-fight boxing glove."""

    def __init__(self):
        self.items = []
        self.glove_glow = None

    def attach(self, cyto_widget: "CytoWidget") -> None:
        """
        Attach a Stewie-style bonnet to the head and a boxing-glove prop to the right arm.

        Parameters:
            cyto_widget: Widget whose head and right arm receive the costume elements.
        """
        # Bonnet — an elongated dome (a gentler nod to Stewie's distinctive
        # football-shaped head than the previous, too-rounded version)
        # with a proper two-loop bow at the crown and a chin strap, worn
        # purely as headwear. Cyto's body is ~44px wide at this height
        # (base_radius 45), so the bonnet's base is widened to match —
        # the previous ±20 base left most of his head visibly uncovered
        # on both sides, reading as a hat perched on top rather than fitted.
        self.bonnet = QGraphicsPathItem()
        b_path = QPainterPath()
        b_path.moveTo(-40, 2)
        b_path.cubicTo(-42, -28, -20, -50, 0, -52)
        b_path.cubicTo(20, -50, 42, -28, 40, 2)
        b_path.cubicTo(22, -8, -22, -8, -40, 2)
        b_path.closeSubpath()
        self.bonnet.setPath(b_path)
        bonnet_grad = QLinearGradient(-40, -52, 40, 2)
        bonnet_grad.setColorAt(0, QColor("#fdfaf3"))
        bonnet_grad.setColorAt(1, QColor("#e8ddc7"))
        self.bonnet.setBrush(QBrush(bonnet_grad))
        self.bonnet.setPen(QPen(QColor("#c9bd9e"), 1.5))
        self.bonnet.setParentItem(cyto_widget.cyto_group)
        self.bonnet.setZValue(6)
        self.items.append(self.bonnet)

        self.strap = QGraphicsPathItem()
        s_path = QPainterPath()
        s_path.moveTo(-40, 2)
        s_path.quadTo(0, 16, 40, 2)
        self.strap.setPath(s_path)
        self.strap.setPen(
            QPen(QColor("#2f5fa8"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        self.strap.setParentItem(cyto_widget.cyto_group)
        self.strap.setZValue(6.1)
        self.items.append(self.strap)

        self.bow = QGraphicsItemGroup()
        self.bow.setParentItem(cyto_widget.cyto_group)
        self.bow.setZValue(6.1)
        self.items.append(self.bow)

        for side in (-1, 1):
            loop = QGraphicsEllipseItem(-5, -3, 10, 6)
            loop.setBrush(QBrush(QColor("#2f5fa8")))
            loop.setPen(QPen(QColor("#1c3f73"), 1))
            loop.setParentItem(self.bow)
            loop.setPos(side * 6, -52)
            loop.setRotation(side * 25)

        knot = QGraphicsEllipseItem(-2.5, -2.5, 5, 5)
        knot.setBrush(QBrush(QColor("#1c3f73")))
        knot.setPen(QPen(Qt.PenStyle.NoPen))
        knot.setParentItem(self.bow)
        knot.setPos(0, -52)

        # Chicken-fight boxing glove — a nod to the show's recurring
        # Peter-vs-Giant-Chicken brawl gag, held like the other props.
        self.glove = QGraphicsPathItem()
        g_path = QPainterPath()
        g_path.addEllipse(-16, -13, 32, 26)
        g_path.addRect(-16, -6, 14, 12)
        self.glove.setPath(g_path.simplified())
        glove_grad = QRadialGradient(-4, 0, 20)
        glove_grad.setColorAt(0, QColor("#f15a42"))
        glove_grad.setColorAt(1, QColor("#c93a24"))
        self.glove.setBrush(QBrush(glove_grad))
        self.glove.setPen(QPen(QColor("#8a2415"), 1.5))
        self.glove.setParentItem(cyto_widget.right_arm)
        self.glove.setPos(52, 0)
        self.items.append(self.glove)

        self.cuff = QGraphicsRectItem(-6, -11, 8, 22)
        self.cuff.setBrush(QBrush(QColor("#f2eee6")))
        self.cuff.setPen(QPen(QColor("#c9bd9e"), 1))
        self.cuff.setParentItem(self.glove)
        self.cuff.setPos(-14, 0)

        self.glove_glow = apply_glow_effect(self.glove, QColor(232, 70, 47), blur_radius=8)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach and remove all costume items from the scene.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:  # noqa: ARG002
        """
        Give the glove a slow, gentle glow pulse — deliberately light on
        motion rather than a flashy "impact" effect competing for attention.
        """
        if self.glove_glow:
            self.glove_glow.setBlurRadius(8 + math.sin(time_step * 1.2) * 3)


class AvatarAangCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.swirl = None

    def attach(self, cyto_widget: "CytoWidget") -> None:
        """
        Attach the arrow, staff, glider wings, and animated airbending swirl to the widget.

        Parameters:
            cyto_widget: Widget whose graphics groups receive the costume elements.
        """
        # Sized and lifted so its base clears the eyes' top edge (y=-15)
        # with a few pixels of gap, instead of the old, smaller arrow
        # whose tip dipped into the eye area.
        self.arrow = QGraphicsPathItem()
        path = QPainterPath()
        path.moveTo(0, -42)
        path.lineTo(6, -30)
        path.lineTo(3, -30)
        path.lineTo(3, -18)
        path.lineTo(-3, -18)
        path.lineTo(-3, -30)
        path.lineTo(-6, -30)
        path.closeSubpath()
        self.arrow.setPath(path)
        self.arrow.setBrush(QBrush(QColor(135, 206, 235)))
        self.arrow.setPen(QPen(Qt.PenStyle.NoPen))
        self.arrow.setParentItem(cyto_widget.cyto_group)
        self.arrow.setZValue(6)

        apply_glow_effect(self.arrow, QColor(135, 206, 235), blur_radius=15)
        self.items.append(self.arrow)

        self.staff = QGraphicsRectItem(45, -60, 4, 90)
        s_grad = QLinearGradient(45, 0, 49, 0)
        s_grad.setColorAt(0, QColor("#a67c52"))
        s_grad.setColorAt(0.5, QColor("#8a5f3a"))
        s_grad.setColorAt(1, QColor("#593e26"))
        self.staff.setBrush(QBrush(s_grad))
        self.staff.setPen(QPen(QColor("#3d2a18"), 0.5))
        self.staff.setParentItem(cyto_widget.right_arm)
        self.items.append(self.staff)

        # Glider wings — closed leaf shapes (two quadratic curves meeting
        # at both tips) instead of the old open path, which Qt was filling
        # by silently straight-lining the gap and rendering as a stray
        # shard. Curvature deepened so they read as crafted glider fabric
        # rather than a thin rect with two small leaf shapes bolted on.
        self.wing1 = QGraphicsPathItem()
        w1_path = QPainterPath()
        w1_path.moveTo(45, -52)
        w1_path.quadTo(22, -44, 45, -35)
        w1_path.quadTo(39, -44, 45, -52)
        w1_path.closeSubpath()
        self.wing1.setPath(w1_path)
        wing_grad1 = QLinearGradient(22, -52, 45, -35)
        wing_grad1.setColorAt(0, QColor("#ffb703"))
        wing_grad1.setColorAt(1, QColor("#ff8c00"))
        self.wing1.setBrush(QBrush(wing_grad1))
        self.wing1.setPen(QPen(QColor("#c96f00"), 1))
        self.wing1.setParentItem(cyto_widget.right_arm)
        self.items.append(self.wing1)

        self.wing2 = QGraphicsPathItem()
        w2_path = QPainterPath()
        w2_path.moveTo(49, -52)
        w2_path.quadTo(72, -44, 49, -35)
        w2_path.quadTo(55, -44, 49, -52)
        w2_path.closeSubpath()
        self.wing2.setPath(w2_path)
        wing_grad2 = QLinearGradient(49, -52, 72, -35)
        wing_grad2.setColorAt(0, QColor("#ffb703"))
        wing_grad2.setColorAt(1, QColor("#ff8c00"))
        self.wing2.setBrush(QBrush(wing_grad2))
        self.wing2.setPen(QPen(QColor("#c96f00"), 1))
        self.wing2.setParentItem(cyto_widget.right_arm)
        self.items.append(self.wing2)

        # Airbending halo — a soft breathing ring of energy at the staff's
        # tip. A fast-spinning triskelion here previously read as a toy
        # pinwheel-on-a-stick rather than airbending energy; a still,
        # gently pulsing ring avoids that "childish" impression.
        self.swirl = QGraphicsEllipseItem(-10, -10, 20, 20)
        self.swirl.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.swirl.setPen(QPen(QColor(200, 235, 255, 180), 2))
        self.swirl.setParentItem(cyto_widget.right_arm)
        self.swirl.setPos(47, -68)
        self.swirl.setZValue(2)
        self.items.append(self.swirl)

        apply_glow_effect(self.swirl, QColor(135, 206, 235), blur_radius=14)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach all costume items and clear the swirl reference.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()
        self.swirl = None

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:  # noqa: ARG002
        """
        Give the staff-tip halo a slow, gentle breathing pulse.
        """
        if self.swirl:
            pulse = 1.0 + math.sin(time_step * 2) * 0.15
            self.swirl.setScale(pulse)
            self.swirl.setOpacity(0.6 + math.sin(time_step * 2) * 0.2)


class AvatarKorraCostume(CytoCostume):
    def __init__(self):
        self.items = []

    def attach(self, cyto_widget: "CytoWidget") -> None:
        """
        Attach Sokka's boomerang to the right arm and a Water Tribe pendant to the body.

        Parameters:
            cyto_widget: Widget whose right arm and body receive the costume elements.
        """
        # Sokka's boomerang — an angular, riveted blue-white blade (the
        # canonical look, not a curved wooden banana shape), held still
        # so it reads as a carried weapon, not a toy in motion.
        self.boomerang = QGraphicsPathItem()
        b_path = QPainterPath()
        b_path.moveTo(0, 4)
        b_path.lineTo(6, -4)
        b_path.lineTo(40, -32)
        b_path.lineTo(34, -26)
        b_path.lineTo(14, -6)
        b_path.lineTo(26, 14)
        b_path.lineTo(18, 16)
        b_path.lineTo(2, 8)
        b_path.closeSubpath()
        self.boomerang.setPath(b_path)
        boomerang_grad = QLinearGradient(0, 4, 40, -32)
        boomerang_grad.setColorAt(0, QColor("#dfeeff"))
        boomerang_grad.setColorAt(0.5, QColor("#8fb8e0"))
        boomerang_grad.setColorAt(1, QColor("#3f6fa0"))
        self.boomerang.setBrush(QBrush(boomerang_grad))
        self.boomerang.setPen(QPen(QColor("#1c3f5c"), 1.5))
        self.boomerang.setParentItem(cyto_widget.right_arm)
        self.boomerang.setPos(46, -6)
        self.items.append(self.boomerang)

        self.boomerang_highlight = QGraphicsPathItem()
        h_path = QPainterPath()
        h_path.moveTo(6, -4)
        h_path.lineTo(38, -31)
        self.boomerang_highlight.setPath(h_path)
        self.boomerang_highlight.setPen(QPen(QColor(255, 255, 255, 160), 1))
        self.boomerang_highlight.setParentItem(self.boomerang)
        self.items.append(self.boomerang_highlight)

        for rx, ry in [(20, -14), (10, 2)]:
            rivet = QGraphicsEllipseItem(-1.6, -1.6, 3.2, 3.2)
            rivet.setBrush(QBrush(QColor("#c9d8e8")))
            rivet.setPen(QPen(QColor("#1c3f5c"), 0.8))
            rivet.setParentItem(self.boomerang)
            rivet.setPos(rx, ry)

        # Water Tribe pendant — a carved crescent-moon medallion, the
        # show's most recognizable prop after bending itself, in the pale
        # bone/ice tone it's traditionally carved from, with a dark
        # leather-choker backing so it stands out from the body clearly.
        self.necklace_backing = QGraphicsEllipseItem(-10, -10, 20, 20)
        self.necklace_backing.setBrush(QBrush(QColor("#16232b")))
        self.necklace_backing.setPen(QPen(QColor("#0d1a20"), 1))
        self.necklace_backing.setParentItem(cyto_widget.cyto_group)
        self.necklace_backing.setPos(0, 32)
        self.necklace_backing.setZValue(2.9)
        self.items.append(self.necklace_backing)

        self.necklace = QGraphicsPathItem()
        n_path = QPainterPath()
        n_path.addEllipse(-8, -8, 16, 16)
        moon_cut = QPainterPath()
        moon_cut.addEllipse(-4.5, -8, 12.5, 16)
        n_path = n_path.subtracted(moon_cut)
        self.necklace.setPath(n_path)
        necklace_grad = QRadialGradient(-2, -2, 9)
        necklace_grad.setColorAt(0, QColor(255, 255, 255))
        necklace_grad.setColorAt(0.6, QColor(212, 240, 255))
        necklace_grad.setColorAt(1, QColor(142, 205, 245))
        self.necklace.setBrush(QBrush(necklace_grad))
        self.necklace.setPen(QPen(QColor("#3d6a8a"), 1.2))
        self.necklace.setParentItem(cyto_widget.cyto_group)
        self.necklace.setPos(0, 32)
        self.necklace.setZValue(3)
        apply_glow_effect(self.necklace, QColor(212, 240, 255), blur_radius=8)
        self.items.append(self.necklace)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """Detach and remove all costume items from the scene."""
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()


class DefaultCostume(CytoCostume):
    def __init__(self):
        self.items = []
        self.medallion = None

    def attach(self, cyto_widget: "CytoWidget") -> None:
        """
        Attach a glowing pointer and a kolam medallion pendant to the widget.

        Parameters:
            cyto_widget: Widget whose right arm and body receive the accessories.
        """
        # A sleek, dark-metallic sci-fi baton with a neon energy core,
        # an angled emitter shroud, and a floating holographic halo
        # orbiting a glowing energy orb at the tip.
        self.pointer = QGraphicsPathItem()
        p_path = QPainterPath()
        p_path.moveTo(45, -3)
        p_path.lineTo(60, -3)
        p_path.lineTo(66, -1.5)
        p_path.lineTo(66, 1.5)
        p_path.lineTo(60, 3)
        p_path.lineTo(45, 3)
        p_path.closeSubpath()
        self.pointer.setPath(p_path)
        pointer_grad = QLinearGradient(45, -3, 45, 3)
        pointer_grad.setColorAt(0.0, QColor("#1e2d3d"))
        pointer_grad.setColorAt(0.5, QColor("#3b4f61"))
        pointer_grad.setColorAt(1.0, QColor("#111a24"))
        self.pointer.setBrush(QBrush(pointer_grad))
        self.pointer.setPen(QPen(QColor("#54728f"), 1))
        self.pointer.setParentItem(cyto_widget.right_arm)
        self.items.append(self.pointer)

        self.neon_core = QGraphicsPathItem()
        core_path = QPainterPath()
        core_path.moveTo(48, 0)
        core_path.lineTo(63, 0)
        self.neon_core.setPath(core_path)
        self.neon_core.setPen(
            QPen(QColor("#58a6ff"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        self.neon_core.setParentItem(cyto_widget.right_arm)
        self.items.append(self.neon_core)
        apply_glow_effect(self.neon_core, QColor("#58a6ff"), blur_radius=6)

        self.emitter = QGraphicsPathItem()
        em_path = QPainterPath()
        em_path.moveTo(63, -4)
        em_path.lineTo(67, -2)
        em_path.lineTo(67, 2)
        em_path.lineTo(63, 4)
        self.emitter.setPath(em_path)
        self.emitter.setPen(
            QPen(QColor("#58a6ff"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        )
        self.emitter.setParentItem(cyto_widget.right_arm)
        self.items.append(self.emitter)

        self.pointer_orb = QGraphicsEllipseItem(-4, -4, 8, 8)
        orb_grad = QRadialGradient(-1, -1, 4)
        orb_grad.setColorAt(0, QColor("#ffffff"))
        orb_grad.setColorAt(0.4, QColor("#58a6ff"))
        orb_grad.setColorAt(1, QColor("#1f6feb"))
        self.pointer_orb.setBrush(QBrush(orb_grad))
        self.pointer_orb.setPen(QPen(Qt.PenStyle.NoPen))
        self.pointer_orb.setParentItem(cyto_widget.right_arm)
        self.pointer_orb.setPos(70, 0)
        self.items.append(self.pointer_orb)
        apply_glow_effect(self.pointer_orb, QColor("#58a6ff"), blur_radius=12)

        self.halo = QGraphicsEllipseItem(-8, -3, 16, 6)
        self.halo.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.halo.setPen(QPen(QColor("#a5d6ff"), 1.5, Qt.PenStyle.DashLine))
        self.halo.setParentItem(cyto_widget.right_arm)
        self.halo.setPos(70, 0)
        self.halo.setRotation(-15)
        self.items.append(self.halo)
        apply_glow_effect(self.halo, QColor("#58a6ff"), blur_radius=8)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach and remove all costume items from the scene.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()
        self.medallion = None

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:  # noqa: ARG002
        """
        Give the kolam medallion a gentle shimmer.
        """
        pass


class AccessibleCostume(CytoCostume):
    """Small, muted raised Braille-dot badge for the Accessible (Okabe-Ito) theme."""

    def __init__(self):
        self.items = []
        self.badge_glow = None

    def attach(self, cyto_widget: "CytoWidget") -> None:
        """
        Attach a small, softly-lit Braille-dot badge to the widget's shoulder.

        Parameters:
            cyto_widget: Widget whose body receives the badge.
        """
        # Sized to a real Braille cell's tall, narrow proportions instead
        # of a square tile — a square 2x3 dot grid on a dark square plaque
        # reads as a die/domino face, not Braille. Kept small and
        # translucent so it accents rather than competes with the
        # character for attention.
        self.plaque = QGraphicsPathItem()
        plaque_path = QPainterPath()
        plaque_path.addRoundedRect(-7, -11, 14, 22, 4, 4)
        self.plaque.setPath(plaque_path)
        self.plaque.setBrush(QBrush(QColor(20, 30, 38, 110)))
        self.plaque.setPen(QPen(QColor("#56B4E9"), 1))
        self.plaque.setParentItem(cyto_widget.cyto_group)
        self.plaque.setPos(-30, 6)
        self.plaque.setZValue(3)
        self.items.append(self.plaque)

        for row in range(3):
            for col in range(2):
                dot = QGraphicsEllipseItem(-1.6, -1.6, 3.2, 3.2)
                dot.setPos(-3.5 + col * 7, -6 + row * 6)
                # Highlight offset toward one corner so each dot reads as
                # a raised tactile bump rather than a flat printed pip.
                dot_grad = QRadialGradient(-0.6, -0.6, 3)
                dot_grad.setColorAt(0, QColor("#ffffff"))
                dot_grad.setColorAt(0.6, QColor("#56B4E9"))
                dot_grad.setColorAt(1, QColor("#0072B2"))
                dot.setBrush(QBrush(dot_grad))
                dot.setPen(QPen(QColor("#0072B2"), 0.4))
                dot.setParentItem(self.plaque)

        self.badge_glow = apply_glow_effect(self.plaque, QColor("#56B4E9"), blur_radius=6)

    def detach(self, cyto_widget: "CytoWidget") -> None:  # noqa: ARG002
        """
        Detach and remove all costume items from the scene.
        """
        for item in self.items:
            item.setParentItem(None)
            if item.scene():
                item.scene().removeItem(item)
        self.items.clear()

    def animate(self, cyto_widget: "CytoWidget", time_step: float) -> None:  # noqa: ARG002
        """
        Give the badge a slow, subtle glow pulse rather than an attention-grabbing one.
        """
        if self.badge_glow:
            self.badge_glow.setBlurRadius(6 + math.sin(time_step * 1.5) * 2)


class CostumeFactory:
    @staticmethod
    def get_costume(theme_name: str) -> CytoCostume:
        """
        Select a costume based on the theme name.

        Parameters:
                theme_name (str): Theme name used to identify the matching costume.

        Returns:
                CytoCostume: The costume associated with the theme, or the default costume when no theme matches.
        """
        name = theme_name.lower()
        if "accessible" in name or "okabe" in name:
            return AccessibleCostume()
        if "galactic" in name:
            # Each variant gets its own hue as a light-toned glow around a
            # near-white blade core — Dark Side is Sith red, Imperial is a
            # distinct amber/orange, Light Side is classic Jedi blue.
            if "dark" in name:
                return GalacticCostume(glow_color="#ff6b5c", core_tint="#fff1ef")
            if "imperial" in name:
                return GalacticCostume(glow_color="#ff9d35", core_tint="#fff7ec")
            return GalacticCostume(glow_color="#58a6ff", core_tint="#eaf4ff")
        if "guild tracker" in name or "mandalorian" in name:
            return MandalorianCostume()
        if "tri-state" in name or "innovation" in name:
            return TriStateCostume()
        if "sub-cavern" in name or "subcavern" in name or "slugterra" in name:
            return SubcavernCostume()
        if "quahog" in name or "family guy" in name:
            return FamilyGuyCostume()
        if "aeroflow" in name or "zen" in name or "aang" in name:
            return AvatarAangCostume()
        if "hydroflow" in name or "polar" in name or "korra" in name:
            return AvatarKorraCostume()
        return DefaultCostume()
