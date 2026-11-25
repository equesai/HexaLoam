function sp = hexaloam_connect(port, baud)
%HEXALOAM_CONNECT Open USB Serial connection to HexaLoam ESP32 actuator slave.
%   NOTE: Standard MG996R servos do not provide external position feedback;
%   returned telemetry reflects commanded targets, not measured joint angles.
    if nargin < 2, baud = 460800; end
    sp = serialport(port, baud, 'Timeout', 1.0);
    configureTerminator(sp, "LF");
    writeline(sp, '{"cmd":"HELLO"}');
end
