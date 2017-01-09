%%  Plots for PSD Size v. Ori
% Will & Wei
% First Load in the Matlab file with the results and source data
%<connectorID> <preSkelID> <preSkelOri> <postSkelID> <postSkelOri> <x> <y> <z>

%% Figure A
delta = SynListOri(:,3) - SynListOri(:,5);

goodIdx = find(~isnan(delta));
delta = abs(delta(goodIdx,:));

delta(delta>90) = 180-delta(delta>90);

figure(101)
plot(delta,sStrength,'o')
grid on
xlabel('delOri')
ylabel('PSD interface (pixels)')
title('Delta Orientation vs PSD Interface Size')
set(gcf,'Color',[1 1 1])

%% Figure A - Part 2
criticalIdx =  find(~isnan(SynListOri(:,3)) & ~isnan(SynListOri(:,5)));
delta = abs(SynListOri(criticalIdx,3) - SynListOri(criticalIdx,5));
delta(delta>90) = 180-delta(delta>90);

figure(101)
plot(delta,sStrength,'o')
grid on
xlabel('delOri')
ylabel('PSD interface (pixels)')
title('Delta Orientation vs PSD Interface Size')
set(gcf,'Color',[1 1 1])

%% 

%% Figure A - Part 3 - 0531
criticalIdx =  find(~isnan(SynListOri(:,3)) & ~isnan(SynListOri(:,5)));
delta = abs(SynListOri(criticalIdx,3) - SynListOri(criticalIdx,5));
delta(delta>90) = 180-delta(delta>90);

figure(101)
plot(delta(mem),sStrength(mem),'o')
grid on
xlabel('delOri')
ylabel('PSD interface (pixels)')
title('Delta Orientation vs PSD Interface Size')
set(gcf,'Color',[1 1 1])
%% 
c  = 1;
criticalSynListOri = SynListOri(criticalIdx,:);

uid = unique(criticalSynListOri(:,2));

for i = 1:length(uid)
    preId = uid(i);
    
    idx = find(criticalSynListOri(:,2) == preId);
    
    postId = unique(criticalSynListOri(idx,4));
    
    for j = 1:length(postId)
        idxEqual = find(criticalSynListOri(idx,4) == postId(j));
        remapIdx = idx(idxEqual); %remap
        
        resultGrouping(c).preId = preId;
        resultGrouping(c).postId = postId(j);
        resultGrouping(c).delOri = delta(remapIdx(1));
        resultGrouping(c).medianWeight = median(sStrength(remapIdx));
        resultGrouping(c).sumWeight = sum(sStrength(remapIdx));
        resultGrouping(c).nSyn = length(remapIdx);
        
        
        c = c + 1;
    end
    
    
end

figure(101)
plot([resultGrouping.delOri],[resultGrouping.nSyn],'o')
grid on
xlabel('delOri')
ylabel('PSD interface (pixels)')
title('Delta Orientation vs PSD Interface Size')
set(gcf,'Color',[1 1 1])


%% Figure B

% Find unique preSkelID
idPre = unique(SynListOri(:,2));

for i = 1:length(idPre)
    groupIdx = find(idPre(i) == SynListOri(:,2));
    
    if length(groupIdx > 1) %can't cluster singleton - should this be weighted?
        meanGroup(i) = mean(sStrength(groupIdx));
        stdGroup(i) = std(sStrength(groupIdx));
    end
end

figure(102)
boxplot(sStrength,SynListOri(:,2))
set(gca,'XTickLabel',num2str([1:length(idPre)]))
set(gca,'YLim',[0,2500])
xlabel('Unique Axons (pre-synaptic partners)')
ylabel('PSD interface size (pixels)')
title('Axon ID vs PSD Interface Size')
set(gcf,'Color',[1 1 1])


%% Figure C

idPost = unique(SynListOri(:,4));

for i = 1:length(idPost)
    groupIdx = find(idPost(i) == SynListOri(:,4));
    
    if length(groupIdx > 1) %can't cluster singleton - should this be weighted?
        meanGroupPost(i) = mean(sStrength(groupIdx));
        stdGroupPost(i) = std(sStrength(groupIdx));
    end
end

figure(103)
boxplot(sStrength,SynListOri(goodIdx,4))
set(gca,'XTickLabel',num2str([1:length(idPre)]))
set(gca,'YLim',[0,2500])
xlabel('Unique Dendrites (post-synaptic partners)')
ylabel('PSD interface size (pixels)')
title('Dendrite ID vs PSD Interface Size')
set(gcf,'Color',[1 1 1])
%% Figure D
figure(104)
plot(SynListOri(goodIdx,3),sStrength,'o')
grid on
xlabel('Pre-Synaptic Partner Orientation')
ylabel('PSD interface size (pixels)')
title('Orientation vs PSD Interface Size')
set(gcf,'Color',[1 1 1])
