"""Vega robots: pick a model by the robot's hardware instead of by file name.

A Vega body ships with a choice of end effector, and later Vega hardware drops the
wrist force/torque (FT) sensor, which moves the tool frame 30.2 mm toward the
shoulder. Loading a model built for other hardware silently puts the tool frame in
the wrong place, so ``get_model`` asks for every option explicitly::

    from dexmate_urdf import vega

    model = vega.get_model("vega_1p", end_effector="f5d6", wrist_ft=False)
    model.urdf, model.srdf, model.collision_spheres_urdf

The wrist option exists only on Vega, which is why this lives in its own module
rather than behind a package-wide ``get_model``.

``BODIES`` is also the build matrix: ``scripts/workflows/generate_variants.py``
reads it to decide which variant files to generate, and takes the modules for a
body from ``variants/<family>/``. Bodies in one family are built from the same
modules, so adding a body to an existing family is one entry here, while a body
with its own end effectors or wrist gets its own family folder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .robots.paths import URDFModel

EndEffector = Literal["gripper", "f5d6"]


@dataclass(frozen=True)
class Body:
    """A hand-authored body and the options its variants are built with.

    Attributes:
        family: Which ``variants/<family>/`` modules apply to this body.
        end_effectors: End effectors it is built with; ``None`` is the bare body.
        wrist_ft: Wrist options. ``True`` is the wrist FT sensor that the body URDF
            is drawn with, ``False`` the shorter flange fitted without the sensor.
    """

    family: str
    end_effectors: tuple[EndEffector | None, ...]
    wrist_ft: tuple[bool, ...]


BODIES: dict[str, Body] = {
    "vega_1": Body("vega_1", (None, "gripper", "f5d6"), (True,)),
    "vega_1u": Body("vega_1", (None, "gripper", "f5d6"), (True, False)),
    "vega_1p": Body("vega_1", (None, "gripper", "f5d6"), (True, False)),
}


@dataclass(frozen=True)
class VegaVariant:
    """One combination of Vega body, end effector, and wrist."""

    body: str
    end_effector: EndEffector | None
    wrist_ft: bool

    @property
    def name(self) -> str:
        """File stem of this variant, e.g. ``vega_1p_no_ft_f5d6``."""
        name = self.body if self.wrist_ft else f"{self.body}_no_ft"
        return name if self.end_effector is None else f"{name}_{self.end_effector}"

    @property
    def family(self) -> str:
        """Family whose modules build this variant."""
        return BODIES[self.body].family


def list_variants(body: str | None = None) -> list[VegaVariant]:
    """List the variants that are built, for one body or for all of them."""
    names = list(BODIES) if body is None else [_check_body(body)]
    return [
        VegaVariant(name, end_effector, wrist_ft)
        for name in names
        for wrist_ft in BODIES[name].wrist_ft
        for end_effector in BODIES[name].end_effectors
    ]


def get_model(
    body: str, *, end_effector: EndEffector | None, wrist_ft: bool
) -> URDFModel:
    """Get the model that matches a robot's hardware.

    Every option is required so that a caller never falls back to a default that
    does not match the robot. On a connected robot, the end effector comes from the
    hand type query and ``wrist_ft`` from the force torque sensor query.

    Args:
        body: Body name, e.g. ``"vega_1p"``.
        end_effector: ``"gripper"``, ``"f5d6"``, or ``None`` for the bare body.
        wrist_ft: Whether the wrist force/torque sensor is fitted.

    Returns:
        The URDF model, with its SRDF and collision spheres URDF alongside.

    Raises:
        TypeError: If ``wrist_ft`` is not a bool.
        ValueError: If the body, end effector, or wrist option is not built.
        FileNotFoundError: If the variant files are missing from the package.
    """
    _check_body(body)
    if end_effector not in BODIES[body].end_effectors:
        raise ValueError(
            f"{body} is not built with end effector {end_effector!r}; "
            f"expected one of {BODIES[body].end_effectors}"
        )
    if not isinstance(wrist_ft, bool):
        raise TypeError(f"wrist_ft must be a bool, got {wrist_ft!r}")
    if wrist_ft not in BODIES[body].wrist_ft:
        fitted = "with" if BODIES[body].wrist_ft[0] else "without"
        raise ValueError(f"{body} is only built {fitted} a wrist FT sensor")

    variant = VegaVariant(body, end_effector, wrist_ft)
    model = URDFModel("humanoid", body, variant.name)
    if not model.urdf.exists():
        raise FileNotFoundError(f"Variant {variant.name} not found: {model.urdf}")
    return model


def _check_body(body: str) -> str:
    if body not in BODIES:
        raise ValueError(f"Unknown body {body!r}; expected one of {tuple(BODIES)}")
    return body
