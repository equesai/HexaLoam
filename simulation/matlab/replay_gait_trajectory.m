function tbl = replay_gait_trajectory(csvPath, sp)
%REPLAY_GAIT_TRAJECTORY Load a HexaLoam CSV trajectory and optionally stream to ESP32.
%   tbl = replay_gait_trajectory('demonstrations/tripod/tripod_trajectory.csv')
    tbl = readtable(csvPath);
    if nargin >= 2 && ~isempty(sp)
        writeline(sp, '{"cmd":"ARM"}');
        dt = median(diff(tbl.time_s));
        for k = 1:height(tbl)
            q = table2array(tbl(k, 2:19));
            msg = sprintf('{"cmd":"SET_JOINTS","rad":[%s]}', strjoin(compose('%.4f', q), ','));
            writeline(sp, msg);
            pause(max(0.005, dt));
        end
    end
end
