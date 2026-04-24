function sweep_compare
% Compare laser sweep .mat files.
% Modes:
%   all  : plot every sweep, no legends (colormap)
%   edge : only first and last sweep with legends
%
% Figures:
%   1 Voltage (odd index points)
%   2 Temperature (even index points)
%   3 Power2 (normalized, inverted)
%   4 Power3 (normalized, inverted)
%   5 Power4 (normalized, inverted)

%% User interaction
dataFolder = uigetdir(pwd,'Select sweep data folder');
if isequal(dataFolder,0); disp('User cancelled.'); return; end
choice = questdlg('Select plot mode','Plot Mode', ...
    'All sweeps (no legend)','First & Last (with legend)','First & Last (with legend)');
plotMode = iff(strcmp(choice,'All sweeps (no legend)'),'all','edge');
doSave = strcmp(questdlg('Save figures as PNG?','Save','Yes','No','No'),'Yes');

%% Files
allFiles = dir(fullfile(dataFolder,'laser_sweep_*.mat'));
if isempty(allFiles)
    error('No files matching laser_sweep_*.mat in %s', dataFolder);
end
nums = nan(1,numel(allFiles));
for k=1:numel(allFiles)
    tok = regexp(allFiles(k).name,'laser_sweep_(\d+)\.mat','tokens','once');
    if ~isempty(tok), nums(k)=str2double(tok{1}); end
end
[~,ord]=sort(nums);
filesSorted = allFiles(ord);

switch plotMode
    case 'all'
        loopIdx = 1:numel(filesSorted); useLegend = false;
    case 'edge'
        loopIdx = unique([1 numel(filesSorted)]); useLegend = true;
end

%% Figures
prepFig(1,'Current (mA)','Voltage (V)','Voltage (sampled)');
prepFig(2,'Current (mA)','Temperature (°C)','Temperature (sampled)');
prepFig(3,'Current (mA)','Normalized Power','Channel 2');
prepFig(4,'Current (mA)','Normalized Power','Channel 3');
prepFig(5,'Current (mA)','Normalized Power','Channel 4');

if strcmp(plotMode,'all')
    C = inferno_map(numel(loopIdx));
else
    C = lines(numel(loopIdx));
end

%% Loop
for ii = 1:numel(loopIdx)
    idx = loopIdx(ii);
    S = load(fullfile(dataFolder, filesSorted(idx).name));
    req = {'current','voltage','srs_temps','power2','power3','power4'};
    if any(~isfield(S,req))
        warning('Skipping %s (missing required fields)', filesSorted(idx).name);
        continue;
    end
    current = S.current(:);
    voltage = S.voltage(:);
    temps   = S.srs_temps(:);
    p2 = double(S.power2(:));
    p3 = double(S.power3(:));
    p4 = double(S.power4(:));

    legendEntry = makeLegend(filesSorted(idx), S);
    % Convert current to mA if values look like Amps (max <= 1)
    if ~isempty(current) && max(current) <= 1
        currentPlot = current * 1000; % A -> mA
    else
        currentPlot = current;        % already mA
    end

    % Derive sampling indices to mimic Python pattern:
    % temp_idx = 0:10:end (MATLAB 1-based -> 1:10:end)
    % volt_idx = 5:10:end (0-based) -> MATLAB 1-based 6:10:end
    step = 10;
    % Voltage indices
    if ~isempty(voltage)
        voltIdxPattern = 6:step:numel(current); % candidate indices
        if numel(voltIdxPattern) >= numel(voltage) - 2 && numel(voltIdxPattern) <= numel(voltage) + 2
            volIdx = voltIdxPattern(1:min(numel(voltIdxPattern), numel(voltage)));
        else
            % fallback: spread indices across full range
            volIdx = round(linspace(1, numel(current), numel(voltage)));
        end
    else
        volIdx = [];
    end
    % Temperature indices
    if ~isempty(temps)
        tempIdxPattern = 1:step:numel(current);
        if numel(tempIdxPattern) >= numel(temps) - 2 && numel(tempIdxPattern) <= numel(temps) + 2
            tempIdx = tempIdxPattern(1:min(numel(tempIdxPattern), numel(temps)));
        else
            tempIdx = round(linspace(1, numel(current), numel(temps)));
        end
    else
        tempIdx = [];
    end

    normfun = @(v) (v-min(v))./max(eps,(max(v)-min(v)));
    invNorm = @(v) normfun(max(v)-v);
    col = C(ii,:);

    if ~isempty(volIdx)
        figure(1); plotOpt(currentPlot(volIdx), voltage(1:numel(volIdx)), '-', 2, col, useLegend, legendEntry);
    end
    if ~isempty(tempIdx)
        figure(2); plotOpt(currentPlot(tempIdx), temps(1:numel(tempIdx)), '-', 2, col, useLegend, legendEntry);
    end
    figure(3); plotOpt(currentPlot, invNorm(p2), '-.', 2, col, useLegend, legendEntry);
    figure(4); plotOpt(currentPlot, invNorm(p3), '-.', 2, col, useLegend, legendEntry);
    figure(5); plotOpt(currentPlot, invNorm(p4), '-.', 2, col, useLegend, legendEntry);

    % save last currentPlot for axis limits later
    lastCurrentPlot = currentPlot; %#ok<NASGU>
end

%% Legends & limits
if useLegend
    for f=1:5, figure(f); legend('Interpreter','none','Location','best','FontSize',12, 'EdgeColor', 'none'); end
end
if exist('current','var') && ~isempty(current)
    xl = [min(current) max(current)];
    for f=1:5, figure(f); xlim(xl); end
end

%% Save
if doSave
    outDir = fullfile(dataFolder,'sweep_plots');
    if ~exist(outDir,'dir'), mkdir(outDir); end
    for f=1:5
        figure(f);
        pngPath = fullfile(outDir, sprintf('figure_%d.png',f));
        figPath = fullfile(outDir, sprintf('figure_%d.fig',f));
        exportgraphics(gcf, pngPath, 'Resolution',300);
        % Save MATLAB figure for future editing
        try
            savefig(gcf, figPath);
        catch
            % Fallback for very old MATLAB versions
            saveas(gcf, figPath);
        end
    end
    fprintf('Saved figures to %s\n', outDir);
end
end

%% Helpers
function prepFig(fnum,xlab,ylab,ttl)
figure(fnum); clf; set(gcf,'Color','w');
ax = gca; hold(ax,'on'); grid(ax,'on');
xlabel(ax,xlab,'FontSize',14);
ylabel(ax,ylab,'FontSize',14);
title(ax,ttl,'FontSize',16);
set(ax,'FontSize',14);
end

function plotOpt(x,y,ls,lw,col,useLegend,labelStr)
if useLegend
    plot(x,y,ls,'LineWidth',lw,'Color',col,'DisplayName',labelStr);
else
    plot(x,y,ls,'LineWidth',lw,'Color',col);
end
end

function s = makeLegend(fileStruct, S)
baseName = fileStruct.name(1:end-4);
if isfield(S,'timestamps')
    rawTS = S.timestamps;
    if iscell(rawTS), rawTS = rawTS{1}; end
    if isstring(rawTS), rawTS = char(rawTS); end
    if ischar(rawTS), ts = rawTS(1:min(19,length(rawTS))); else, ts=''; end
else
    ts='';
end
s = sprintf('%s | %s', baseName, ts);
end

function cmap = inferno_map(n)
base = [ ...
0.074 0.016 0.129
0.180 0.022 0.256
0.322 0.025 0.361
0.478 0.016 0.401
0.626 0.062 0.368
0.760 0.166 0.297
0.873 0.299 0.231
0.956 0.455 0.179
0.997 0.642 0.129
0.988 0.816 0.144];
xi = linspace(1,size(base,1),n);
cmap = interp1(1:size(base,1), base, xi);
end

function v = iff(cond,a,b)
if cond, v=a; else, v=b; end
end
