function [footPosition, jacobian, holdingTorque] = legStaticStudy(lengths, angles, tipForce)
%LEGSTATICSTUDY Ideal yaw-pitch-pitch leg with an external force at the foot.
% lengths [m]: horizontal hip offset, thigh length, shank length.
% angles [rad]: yaw, thigh pitch, relative knee pitch. Positive pitch raises
% the foot. At zero angles the three segments point along base-frame +X.
% tipForce [N] acts on the foot, expressed in the hip base frame.
% holdingTorque [N*m] balances only this force in static equilibrium.
arguments
    lengths (3,1) double {mustBeFinite,mustBePositive}
    angles (3,1) double {mustBeFinite}
    tipForce (3,1) double {mustBeFinite}
end
yaw = angles(1);
pitch = angles(2);
kneePitch = pitch + angles(3);
reach = lengths(1) + lengths(2)*cos(pitch) + lengths(3)*cos(kneePitch);
height = lengths(2)*sin(pitch) + lengths(3)*sin(kneePitch);
radial = [cos(yaw); sin(yaw); 0];
vertical = [0; 0; 1];
footPosition = reach*radial + height*vertical;
jacobian = [reach*[-sin(yaw); cos(yaw); 0], ...
    -height*radial + (reach-lengths(1))*vertical, ...
    lengths(3)*(-sin(kneePitch)*radial + cos(kneePitch)*vertical)];
holdingTorque = -jacobian.' * tipForce;
end
