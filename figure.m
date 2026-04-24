figure
set(gca,'FontSize',14)
c1 = [0.074, 0.016, 0.129]; % 
c2 = [0.543, 0.212, 0.470]; 
c3 = [0.988, 0.816, 0.144]; % yellow
hold all

grid on
box on
plot(current_A, channel_3_A, 'LineWidth',2,'Color',c1) %April
plot(current_M, channel_3_M, 'LineWidth',2,'Color',c2) %May
plot(current, channel_3, 'LineWidth',2,'Color',c3) %June
legend('Month1-20250406','Month2-20250509','Month3-20250625') 
xlabel('Current (mA)','FontSize',14) 
ylabel('Power (mW)','FontSize',14)

%% --- Diagnostics & Alignment Add-on ---
% Ensure column vectors
current_A = current_A(:); channel_3_A = channel_3_A(:);
current_M = current_M(:); channel_3_M = channel_3_M(:);
current    = current(:);  channel_3   = channel_3(:);

% Convert to mA if data appears in Amps
if max(current_A)<=1, current_A = current_A*1000; end
if max(current_M)<=1, current_M = current_M*1000; end
if max(current)<=1,   current   = current*1000; end

% Remove duplicates & enforce monotonic ascending order
[current_A, ia] = unique(current_A,'stable'); channel_3_A = channel_3_A(ia);
[current_M, im] = unique(current_M,'stable'); channel_3_M = channel_3_M(im);
[current,  ij]  = unique(current,'stable');   channel_3   = channel_3(ij);

% Replot cleaned data for confirmation
figure('Name','Cleaned Raw'); hold on; grid on; box on; set(gca,'FontSize',14)
plot(current_A, channel_3_A,'LineWidth',2,'Color',c1)
plot(current_M, channel_3_M,'LineWidth',2,'Color',c2)
plot(current,   channel_3,  'LineWidth',2,'Color',c3)
legend('Month1-20250406','Month2-20250509','Month3-20250625','Location','best')
xlabel('Current (mA)','FontSize',14); ylabel('Power (mW)','FontSize',14)
title('Cleaned (unique, monotonic)')

% Common grid interpolation
cmin = max([min(current_A) min(current_M) min(current)]);
cmax = min([max(current_A) max(current_M) max(current)]);
Ncommon = min([numel(current_A) numel(current_M) numel(current)]);
common = linspace(cmin, cmax, Ncommon);
pA_i = interp1(current_A, channel_3_A, common,'linear','extrap');
pM_i = interp1(current_M, channel_3_M, common,'linear','extrap');
pJ_i = interp1(current,   channel_3,   common,'linear','extrap');

figure('Name','Aligned Grid'); hold on; grid on; box on; set(gca,'FontSize',14)
plot(common, pA_i,'LineWidth',2,'Color',c1)
plot(common, pM_i,'LineWidth',2,'Color',c2)
plot(common, pJ_i,'LineWidth',2,'Color',c3)
legend('Month1-20250406','Month2-20250509','Month3-20250625','Location','best')
xlabel('Current (mA)','FontSize',14); ylabel('Power (mW)','FontSize',14)
title('Interpolated to Common Current Grid')

% Normalized domain overlay
tA = (current_A - current_A(1))/(current_A(end)-current_A(1));
tM = (current_M - current_M(1))/(current_M(end)-current_M(1));
tJ = (current    - current(1)) /(current(end)   -current(1));
Nt = min([numel(tA) numel(tM) numel(tJ)]);
tCommon = linspace(0,1,Nt);
pA_t = interp1(tA, channel_3_A, tCommon,'linear','extrap');
pM_t = interp1(tM, channel_3_M, tCommon,'linear','extrap');
pJ_t = interp1(tJ, channel_3,   tCommon,'linear','extrap');

figure('Name','Normalized Progress'); hold on; grid on; box on; set(gca,'FontSize',14)
plot(tCommon, pA_t,'LineWidth',2,'Color',c1)
plot(tCommon, pM_t,'LineWidth',2,'Color',c2)
plot(tCommon, pJ_t,'LineWidth',2,'Color',c3)
legend('Month1-20250406','Month2-20250509','Month3-20250625','Location','best')
xlabel('Normalized current progress','FontSize',14); ylabel('Power (mW)','FontSize',14)
title('Domain Normalized Overlay')

% RMSE metrics
rmse_AM = sqrt(mean((pA_i - pM_i).^2));
rmse_AJ = sqrt(mean((pA_i - pJ_i).^2));
rmse_MJ = sqrt(mean((pM_i - pJ_i).^2));
fprintf('RMSE (common grid): A-M=%.4f  A-J=%.4f  M-J=%.4f\n', rmse_AM, rmse_AJ, rmse_MJ);
