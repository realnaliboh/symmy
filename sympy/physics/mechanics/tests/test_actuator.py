"""Tests for the ``sympy.physics.mechanics._actuator.py`` module."""

from __future__ import annotations

from typing import Any

import pytest

from sympy.core.backend import (
    S,
    USE_SYMENGINE,
    Matrix,
    Symbol,
    SympifyError,
    sqrt,
)
from sympy.physics.mechanics import (
    Force,
    KanesMethod,
    Particle,
    PinJoint,
    Point,
    ReferenceFrame,
    RigidBody,
    Vector,
    dynamicsymbols,
)
from sympy.physics.mechanics._actuator import (
    ActuatorBase,
    ForceActuator,
    LinearDamper,
    LinearSpring,
    TorqueActuator,
)
from sympy.physics.mechanics._pathway import LinearPathway, PathwayBase

if USE_SYMENGINE:
    from sympy.core.backend import Basic as ExprType
else:
    from sympy.core.expr import Expr as ExprType


target = RigidBody('target')
reaction = RigidBody('reaction')


class TestForceActuator:

    @pytest.fixture(autouse=True)
    def _linear_pathway_fixture(self) -> None:
        self.force = Symbol('F')
        self.pA = Point('pA')
        self.pB = Point('pB')
        self.pathway = LinearPathway(self.pA, self.pB)
        self.q1 = dynamicsymbols('q1')
        self.q2 = dynamicsymbols('q2')
        self.q3 = dynamicsymbols('q3')
        self.q1d = dynamicsymbols('q1', 1)
        self.q2d = dynamicsymbols('q2', 1)
        self.q3d = dynamicsymbols('q3', 1)
        self.N = ReferenceFrame('N')

    def test_is_actuator_base_subclass(self) -> None:
        assert issubclass(ForceActuator, ActuatorBase)

    @pytest.mark.parametrize(
        'force, expected_force',
        [
            (1, S.One),
            (S.One, S.One),
            (Symbol('F'), Symbol('F')),
            (dynamicsymbols('F'), dynamicsymbols('F')),
            (Symbol('F')**2 + Symbol('F'), Symbol('F')**2 + Symbol('F')),
        ]
    )
    def test_valid_constructor_force(
        self,
        force: Any,
        expected_force: ExprType,
    ) -> None:
        instance = ForceActuator(force, self.pathway)
        assert isinstance(instance, ForceActuator)
        assert hasattr(instance, 'force')
        assert isinstance(instance.force, ExprType)
        assert instance.force == expected_force

    @pytest.mark.parametrize('force', [None, 'F'])
    def test_invalid_constructor_force_not_sympifyable(
        self,
        force: Any,
    ) -> None:
        with pytest.raises(SympifyError):
            _ = ForceActuator(force, self.pathway)  # type: ignore

    @pytest.mark.parametrize(
        'pathway',
        [
            LinearPathway(Point('pA'), Point('pB')),
        ]
    )
    def test_valid_constructor_pathway(self, pathway: PathwayBase) -> None:
        instance = ForceActuator(self.force, pathway)
        assert isinstance(instance, ForceActuator)
        assert hasattr(instance, 'pathway')
        assert isinstance(instance.pathway, LinearPathway)
        assert instance.pathway == pathway

    def test_invalid_constructor_pathway_not_pathway_base(self) -> None:
        with pytest.raises(TypeError):
            _ = ForceActuator(self.force, None)  # type: ignore

    @pytest.mark.parametrize(
        'property_name, fixture_attr_name',
        [
            ('force', 'force'),
            ('pathway', 'pathway'),
        ]
    )
    def test_properties_are_immutable(
        self,
        property_name: str,
        fixture_attr_name: str,
    ) -> None:
        instance = ForceActuator(self.force, self.pathway)
        value = getattr(self, fixture_attr_name)
        with pytest.raises(AttributeError):
            setattr(instance, property_name, value)

    def test_repr(self) -> None:
        actuator = ForceActuator(self.force, self.pathway)
        expected = "ForceActuator(F, LinearPathway(pA, pB))"
        assert repr(actuator) == expected

    def test_to_loads_static_pathway(self) -> None:
        self.pB.set_pos(self.pA, 2 * self.N.x)
        actuator = ForceActuator(self.force, self.pathway)
        expected = [
            (self.pA, - self.force * self.N.x),
            (self.pB, self.force * self.N.x),
        ]
        assert actuator.to_loads() == expected

    def test_to_loads_2D_pathway(self) -> None:
        self.pB.set_pos(self.pA, 2 * self.q1 * self.N.x)
        actuator = ForceActuator(self.force, self.pathway)
        expected = [
            (self.pA, - self.force * (self.q1 / sqrt(self.q1**2)) * self.N.x),
            (self.pB, self.force * (self.q1 / sqrt(self.q1**2)) * self.N.x),
        ]
        assert actuator.to_loads() == expected

    def test_to_loads_3D_pathway(self) -> None:
        self.pB.set_pos(
            self.pA,
            self.q1*self.N.x - self.q2*self.N.y + 2*self.q3*self.N.z,
        )
        actuator = ForceActuator(self.force, self.pathway)
        length = sqrt(self.q1**2 + self.q2**2 + 4*self.q3**2)
        pO_force = (
            - self.force * self.q1 * self.N.x / length
            + self.force * self.q2 * self.N.y / length
            - 2 * self.force * self.q3 * self.N.z / length
        )
        pI_force = (
            self.force * self.q1 * self.N.x / length
            - self.force * self.q2 * self.N.y / length
            + 2 * self.force * self.q3 * self.N.z / length
        )
        expected = [
            (self.pA, pO_force),
            (self.pB, pI_force),
        ]
        assert actuator.to_loads() == expected


class TestLinearSpring:

    @pytest.fixture(autouse=True)
    def _linear_spring_fixture(self) -> None:
        self.stiffness = Symbol('k')
        self.l = Symbol('l')
        self.pA = Point('pA')
        self.pB = Point('pB')
        self.pathway = LinearPathway(self.pA, self.pB)
        self.q = dynamicsymbols('q')
        self.N = ReferenceFrame('N')

    def test_is_force_actuator_subclass(self) -> None:
        assert issubclass(LinearSpring, ForceActuator)

    def test_is_actuator_base_subclass(self) -> None:
        assert issubclass(LinearSpring, ActuatorBase)

    @pytest.mark.parametrize(
        (
            'stiffness, '
            'expected_stiffness, '
            'equilibrium_length, '
            'expected_equilibrium_length, '
            'force'
        ),
        [
            (
                1,
                S.One,
                0,
                S.Zero,
                -sqrt(dynamicsymbols('q')**2),
            ),
            (
                Symbol('k'),
                Symbol('k'),
                0,
                S.Zero,
                -Symbol('k')*sqrt(dynamicsymbols('q')**2),
            ),
            (
                Symbol('k'),
                Symbol('k'),
                S.Zero,
                S.Zero,
                -Symbol('k')*sqrt(dynamicsymbols('q')**2),
            ),
            (
                Symbol('k'),
                Symbol('k'),
                Symbol('l'),
                Symbol('l'),
                -Symbol('k')*(sqrt(dynamicsymbols('q')**2) - Symbol('l')),
            ),
        ]
    )
    def test_valid_constructor(
        self,
        stiffness: Any,
        expected_stiffness: ExprType,
        equilibrium_length: Any,
        expected_equilibrium_length: ExprType,
        force: ExprType,
    ) -> None:
        self.pB.set_pos(self.pA, self.q * self.N.x)
        spring = LinearSpring(stiffness, self.pathway, equilibrium_length)

        assert isinstance(spring, LinearSpring)

        assert hasattr(spring, 'stiffness')
        assert isinstance(spring.stiffness, ExprType)
        assert spring.stiffness == expected_stiffness

        assert hasattr(spring, 'pathway')
        assert isinstance(spring.pathway, LinearPathway)
        assert spring.pathway == self.pathway

        assert hasattr(spring, 'equilibrium_length')
        assert isinstance(spring.equilibrium_length, ExprType)
        assert spring.equilibrium_length == expected_equilibrium_length

        assert hasattr(spring, 'force')
        assert isinstance(spring.force, ExprType)
        assert spring.force == force

    @pytest.mark.parametrize('stiffness', [None, 'k'])
    def test_invalid_constructor_stiffness_not_sympifyable(
        self,
        stiffness: Any,
    ) -> None:
        with pytest.raises(SympifyError):
            _ = LinearSpring(stiffness, self.pathway, self.l)

    def test_invalid_constructor_pathway_not_pathway_base(self) -> None:
        with pytest.raises(TypeError):
            _ = LinearSpring(self.stiffness, None, self.l)  # type: ignore

    @pytest.mark.parametrize('equilibrium_length', [None, 'l'])
    def test_invalid_constructor_equilibrium_length_not_sympifyable(
        self,
        equilibrium_length: Any,
    ) -> None:
        with pytest.raises(SympifyError):
            _ = LinearSpring(self.stiffness, self.pathway, equilibrium_length)

    @pytest.mark.parametrize(
        'property_name, fixture_attr_name',
        [
            ('stiffness', 'stiffness'),
            ('pathway', 'pathway'),
            ('equilibrium_length', 'l'),
        ]
    )
    def test_properties_are_immutable(
        self,
        property_name: str,
        fixture_attr_name: str,
    ) -> None:
        spring = LinearSpring(self.stiffness, self.pathway, self.l)
        value = getattr(self, fixture_attr_name)
        with pytest.raises(AttributeError):
            setattr(spring, property_name, value)

    @pytest.mark.parametrize(
        'equilibrium_length, expected',
        [
            (S.Zero, 'LinearSpring(k, LinearPathway(pA, pB))'),
            (
                Symbol('l'),
                'LinearSpring(k, LinearPathway(pA, pB), equilibrium_length=l)',
            ),
        ]
    )
    def test_repr(self, equilibrium_length: Any, expected: str) -> None:
        self.pB.set_pos(self.pA, self.q * self.N.x)
        spring = LinearSpring(self.stiffness, self.pathway, equilibrium_length)
        assert repr(spring) == expected

    def test_to_loads(self) -> None:
        self.pB.set_pos(self.pA, self.q * self.N.x)
        spring = LinearSpring(self.stiffness, self.pathway, self.l)
        normal = self.q / sqrt(self.q**2) * self.N.x
        pA_force = self.stiffness * (sqrt(self.q**2) - self.l) * normal
        pB_force = -self.stiffness * (sqrt(self.q**2) - self.l) * normal
        expected = [Force(self.pA, pA_force), Force(self.pB, pB_force)]
        loads = spring.to_loads()

        for load, (point, vector) in zip(loads, expected):
            assert isinstance(load, Force)
            assert load.point == point
            assert (load.vector - vector).simplify() == 0


class TestLinearDamper:

    @pytest.fixture(autouse=True)
    def _linear_damper_fixture(self) -> None:
        self.damping = Symbol('c')
        self.l = Symbol('l')
        self.pA = Point('pA')
        self.pB = Point('pB')
        self.pathway = LinearPathway(self.pA, self.pB)
        self.q = dynamicsymbols('q')
        self.dq = dynamicsymbols('q', 1)
        self.u = dynamicsymbols('u')
        self.N = ReferenceFrame('N')

    def test_is_force_actuator_subclass(self) -> None:
        assert issubclass(LinearDamper, ForceActuator)

    def test_is_actuator_base_subclass(self) -> None:
        assert issubclass(LinearDamper, ActuatorBase)

    def test_valid_constructor(self) -> None:
        self.pB.set_pos(self.pA, self.q * self.N.x)
        damper = LinearDamper(self.damping, self.pathway)

        assert isinstance(damper, LinearDamper)

        assert hasattr(damper, 'damping')
        assert isinstance(damper.damping, ExprType)
        assert damper.damping == self.damping

        assert hasattr(damper, 'pathway')
        assert isinstance(damper.pathway, LinearPathway)
        assert damper.pathway == self.pathway

        expected_force = -self.damping * self.dq * self.q / sqrt(self.q**2)
        assert hasattr(damper, 'force')
        assert isinstance(damper.force, ExprType)
        assert damper.force == expected_force

    @pytest.mark.parametrize('damping', [None, 'c'])
    def test_invalid_constructor_damping_not_sympifyable(
        self,
        damping: Any,
    ) -> None:
        with pytest.raises(SympifyError):
            _ = LinearDamper(damping, self.pathway)

    def test_invalid_constructor_pathway_not_pathway_base(self) -> None:
        with pytest.raises(TypeError):
            _ = LinearDamper(self.damping, None)  # type: ignore

    @pytest.mark.parametrize(
        'property_name, fixture_attr_name',
        [
            ('damping', 'damping'),
            ('pathway', 'pathway'),
        ]
    )
    def test_properties_are_immutable(
        self,
        property_name: str,
        fixture_attr_name: str,
    ) -> None:
        damper = LinearDamper(self.damping, self.pathway)
        value = getattr(self, fixture_attr_name)
        with pytest.raises(AttributeError):
            setattr(damper, property_name, value)

    def test_repr(self) -> None:
        self.pB.set_pos(self.pA, self.q * self.N.x)
        damper = LinearDamper(self.damping, self.pathway)
        expected = 'LinearDamper(c, LinearPathway(pA, pB))'
        assert repr(damper) == expected

    def test_to_loads(self) -> None:
        self.pB.set_pos(self.pA, self.q * self.N.x)
        damper = LinearDamper(self.damping, self.pathway)
        direction = self.q**2 / self.q**2 * self.N.x
        pA_force = self.damping * self.dq * direction
        pB_force = -self.damping * self.dq * direction
        expected = [Force(self.pA, pA_force), Force(self.pB, pB_force)]
        assert damper.to_loads() == expected


class TestForcedMassSpringDamperModel():
    r"""A single degree of freedom translational forced mass-spring-damper.

    Notes
    =====

    This system is well known to have the governing equation:

    .. math::
        m \ddot{x} = F - k x - c \dot{x}

    where $F$ is an externally applied force, $m$ is the mass of the particle
    to which the spring and damper are attached, $k$ is the spring's stiffness,
    $c$ is the dampers damping coefficient, and $x$ is the generalized
    coordinate representing the system's single (translational) degree of
    freedom.

    """

    @pytest.fixture(autouse=True)
    def _force_mass_spring_damper_model_fixture(self) -> None:
        self.m = Symbol('m')
        self.k = Symbol('k')
        self.c = Symbol('c')
        self.F = Symbol('F')

        self.q = dynamicsymbols('q')
        self.dq = dynamicsymbols('q', 1)
        self.u = dynamicsymbols('u')

        self.frame = ReferenceFrame('N')
        self.origin = Point('pO')
        self.origin.set_vel(self.frame, 0)

        self.attachment = Point('pA')
        self.attachment.set_pos(self.origin, self.q * self.frame.x)

        self.mass = Particle('mass', self.attachment, self.m)
        self.pathway = LinearPathway(self.origin, self.attachment)

        self.kanes_method = KanesMethod(
            self.frame,
            q_ind=[self.q],
            u_ind=[self.u],
            kd_eqs=[self.dq - self.u],
        )
        self.bodies = [self.mass]

        self.mass_matrix = Matrix([[self.m]])
        self.forcing = Matrix([[self.F - self.c*self.u - self.k*self.q]])

    def test_force_acuator(self):
        stiffness = -self.k * self.pathway.length
        spring = ForceActuator(stiffness, self.pathway)
        damping = -self.c * self.pathway.extension_velocity
        damper = ForceActuator(damping, self.pathway)

        loads = [
            (self.attachment, self.F * self.frame.x),
            *spring.to_loads(),
            *damper.to_loads(),
        ]
        self.kanes_method.kanes_equations(self.bodies, loads)

        assert self.kanes_method.mass_matrix == self.mass_matrix
        assert self.kanes_method.forcing == self.forcing

    def test_linear_spring_linear_damper(self):
        spring = LinearSpring(self.k, self.pathway)
        damper = LinearDamper(self.c, self.pathway)

        loads = [
            (self.attachment, self.F * self.frame.x),
            *spring.to_loads(),
            *damper.to_loads(),
        ]
        self.kanes_method.kanes_equations(self.bodies, loads)

        assert self.kanes_method.mass_matrix == self.mass_matrix
        assert self.kanes_method.forcing == self.forcing


class TestTorqueActuator:

    @pytest.fixture(autouse=True)
    def _torque_actuator_fixture(self) -> None:
        self.torque = Symbol('T')
        self.N = ReferenceFrame('N')
        self.A = ReferenceFrame('A')
        self.axis = self.N.z
        self.target = RigidBody('target', frame=self.N)
        self.reaction = RigidBody('reaction', frame=self.A)

    def test_is_actuator_base_subclass(self) -> None:
        assert issubclass(TorqueActuator, ActuatorBase)

    @pytest.mark.parametrize(
        'torque',
        [
            Symbol('T'),
            dynamicsymbols('T'),
            Symbol('T')**2 + Symbol('T'),
        ]
    )
    @pytest.mark.parametrize(
        'target_frame, reaction_frame',
        [
            (target.frame, reaction.frame),
            (target, reaction.frame),
            (target.frame, reaction),
            (target, reaction),
        ]
    )
    def test_valid_constructor_with_reaction(
        self,
        torque: ExprType,
        target_frame: ReferenceFrame | RigidBody,
        reaction_frame: ReferenceFrame | RigidBody,
    ) -> None:
        instance = TorqueActuator(
            torque,
            self.axis,
            target_frame,
            reaction_frame,
        )
        assert isinstance(instance, TorqueActuator)

        assert hasattr(instance, 'torque')
        assert isinstance(instance.torque, ExprType)
        assert instance.torque == torque

        assert hasattr(instance, 'axis')
        assert isinstance(instance.axis, Vector)
        assert instance.axis == self.axis

        assert hasattr(instance, 'target_frame')
        assert isinstance(instance.target_frame, ReferenceFrame)
        assert instance.target_frame == target.frame

        assert hasattr(instance, 'reaction_frame')
        assert isinstance(instance.reaction_frame, ReferenceFrame)
        assert instance.reaction_frame == reaction.frame

    @pytest.mark.parametrize(
        'torque',
        [
            Symbol('T'),
            dynamicsymbols('T'),
            Symbol('T')**2 + Symbol('T'),
        ]
    )
    @pytest.mark.parametrize('target_frame', [target.frame, target])
    def test_valid_constructor_without_reaction(
        self,
        torque: ExprType,
        target_frame: ReferenceFrame | RigidBody,
    ) -> None:
        instance = TorqueActuator(torque, self.axis, target_frame)
        assert isinstance(instance, TorqueActuator)

        assert hasattr(instance, 'torque')
        assert isinstance(instance.torque, ExprType)
        assert instance.torque == torque

        assert hasattr(instance, 'axis')
        assert isinstance(instance.axis, Vector)
        assert instance.axis == self.axis

        assert hasattr(instance, 'target_frame')
        assert isinstance(instance.target_frame, ReferenceFrame)
        assert instance.target_frame == target.frame

        assert hasattr(instance, 'reaction_frame')
        assert instance.reaction_frame is None

    @pytest.mark.parametrize('torque', [None, 'T'])
    def test_invalid_constructor_torque_not_sympifyable(
        self,
        torque: Any,
    ) -> None:
        with pytest.raises(SympifyError):
            _ = TorqueActuator(torque, self.axis, self.target)  # type: ignore

    @pytest.mark.parametrize('axis', [Symbol('a'), dynamicsymbols('a')])
    def test_invalid_constructor_axis_not_vector(self, axis: Any) -> None:
        with pytest.raises(TypeError):
            _ = TorqueActuator(self.torque, axis, self.target, self.reaction)  # type: ignore

    @pytest.mark.parametrize(
        'frames',
        [
            (None, ReferenceFrame('child')),
            (ReferenceFrame('parent'), True),
            (None, RigidBody('child')),
            (RigidBody('parent'), True),
        ]
    )
    def test_invalid_constructor_frames_not_frame(
        self,
        frames: tuple[Any, Any],
    ) -> None:
        with pytest.raises(TypeError):
            _ = TorqueActuator(self.torque, self.axis, *frames)  # type: ignore

    @pytest.mark.parametrize(
        'property_name, fixture_attr_name',
        [
            ('torque', 'torque'),
            ('axis', 'axis'),
            ('target_frame', 'target'),
            ('reaction_frame', 'reaction'),
        ]
    )
    def test_properties_are_immutable(
        self,
        property_name: str,
        fixture_attr_name: str,
    ) -> None:
        actuator = TorqueActuator(
            self.torque,
            self.axis,
            self.target,
            self.reaction,
        )
        value = getattr(self, fixture_attr_name)
        with pytest.raises(AttributeError):
            setattr(actuator, property_name, value)

    def test_repr_without_reaction(self) -> None:
        actuator = TorqueActuator(self.torque, self.axis, self.target)
        expected = 'TorqueActuator(T, axis=N.z, target_frame=N)'
        assert repr(actuator) == expected

    def test_repr_with_reaction(self) -> None:
        actuator = TorqueActuator(
            self.torque,
            self.axis,
            self.target,
            self.reaction,
        )
        expected = 'TorqueActuator(T, axis=N.z, target_frame=N, reaction_frame=A)'
        assert repr(actuator) == expected

    def test_at_pin_joint_constructor(self) -> None:
        pin_joint = PinJoint(
            'pin',
            self.target,
            self.reaction,
            coordinates=dynamicsymbols('q'),
            speeds=dynamicsymbols('u'),
            parent_interframe=self.N,
            joint_axis=self.axis,
        )
        instance = TorqueActuator.at_pin_joint(self.torque, pin_joint)
        assert isinstance(instance, TorqueActuator)

        assert hasattr(instance, 'torque')
        assert isinstance(instance.torque, ExprType)
        assert instance.torque == self.torque

        assert hasattr(instance, 'axis')
        assert isinstance(instance.axis, Vector)
        assert instance.axis == self.axis

        assert hasattr(instance, 'target_frame')
        assert isinstance(instance.target_frame, ReferenceFrame)
        assert instance.target_frame == self.A

        assert hasattr(instance, 'reaction_frame')
        assert isinstance(instance.reaction_frame, ReferenceFrame)
        assert instance.reaction_frame == self.N

    def test_at_pin_joint_pin_joint_not_pin_joint_invalid(self) -> None:
        with pytest.raises(TypeError):
            _ = TorqueActuator.at_pin_joint(self.torque, Symbol('pin'))  # type: ignore

    def test_to_loads_without_reaction(self) -> None:
        actuator = TorqueActuator(self.torque, self.axis, self.target)
        expected = [
            (self.N, self.torque * self.axis),
        ]
        assert actuator.to_loads() == expected

    def test_to_loads_with_reaction(self) -> None:
        actuator = TorqueActuator(
            self.torque,
            self.axis,
            self.target,
            self.reaction,
        )
        expected = [
            (self.N, self.torque * self.axis),
            (self.A, - self.torque * self.axis),
        ]
        assert actuator.to_loads() == expected
