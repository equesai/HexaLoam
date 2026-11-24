function tests = testLegStaticStudy
tests = functiontests(localfunctions);
end

function testStraightLeg(testCase)
[position, ~, torque] = legStaticStudy([0.03;0.10;0.12], zeros(3,1), [0;0;-5]);
verifyEqual(testCase, position, [0.25;0;0], 'AbsTol', 1e-12);
verifyEqual(testCase, torque, [0;1.10;0.60], 'AbsTol', 1e-12);
end

function testJacobianAgainstFiniteDifferences(testCase)
lengths = [0.03;0.10;0.12];
angles = [0.48;-0.27;0.91];
force = [3;-2;4];
[~, jacobian, torque] = legStaticStudy(lengths, angles, force);
delta = 1e-6;
for axis = 1:3
    step = zeros(3,1);
    step(axis) = delta;
    plus = legStaticStudy(lengths, angles+step, force);
    minus = legStaticStudy(lengths, angles-step, force);
    column = (plus-minus)/(2*delta);
    verifyEqual(testCase, jacobian(:,axis), column, 'AbsTol', 1e-9);
    verifyEqual(testCase, torque(axis), -dot(force,column), 'AbsTol', 1e-8);
end
end
