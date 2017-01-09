%% Wei Synapse Prototype
%<connectorID> <preSkelID> <preSkelOri> <postSkelID> <postSkelOri> <x> <y> <z>
%W Gray Roncal and WCA Lee 
% Now [Connector# PreSkeleton PostSkeleton X Y Z SynOriPre SynSfPre SynTfPre SynSpeedPre SynOriPost SynSfPost SynTfPost SynSpeedPost]

%load('SynListOriSfTfSpeed_0327')

% This is just an interface to the old code - will need to rework
SynListOri = SynListOriSfTfSpeed(:,[1,2,7,3,11,4,5,6]);

oo = OCP();
oo.setServerLocation('http://dsp029.pha.jhu.edu/');
oo.setImageToken('lee14');
oo.setDefaultResolution(1);
zRange = oo.imageInfo.DATASET.SLICERANGE;

%%

% Identify critical synapses of interest
criticalIdx =  find(~isnan(SynListOri(:,3)) & ~isnan(SynListOri(:,5)));

tic
% Save results
saveFlag = 1;
% Plot results
plotFlag = 1;
% Store data locally
backupFlag = 0;

% Only option right now
method = 1;

padd = 20;

sStrength = zeros(1,size(criticalIdx,1));

% counter
perfCount = 0;

for i = 1:length(criticalIdx)
    toc
    i
    if mod((i),20) == 0
        fprintf('Now processing synapse %d of %d...\n', i, length(criticalIdx));
    end
    %id = SynListOri(i,1);
    xLoc = SynListOri(criticalIdx(i),6);
    yLoc = SynListOri(criticalIdx(i),7);
    zLoc = SynListOri(criticalIdx(i),8);
    
    xLoc = round(xLoc/(4*2)); %scale 1
    yLoc = round(yLoc/(4*2)); %scale 1
    zLoc = zLoc/40; %/40
    
    pad = [100, 100, 12];
    qq = OCPQuery(eOCPQueryType.imageDense);
    qq.setXRange([xLoc-pad(1),xLoc+pad(1)]);
    qq.setYRange([yLoc-pad(2),yLoc+pad(2)]);
    qq.setZRange([max(zLoc-pad(3),zRange(1)),min(zLoc+pad(3)+1,zRange(2))]);
    qq.setResolution(1);
    
    ccount = 0;
    err_count = 0;
    while ccount == err_count
        try
            synIm = oo.query(qq);
            
        catch MyErr
            disp('retrying')
            err_count = err_count + 1;
        end
        ccount = ccount + 1;
    end
    
    synImgData = synIm.data;
    
    if backupFlag
        dataSynListOri{i} = synImgData;
    else
        zz = qq.zRange(1):qq.zRange(end);
        cSlice = find(zz == zLoc); %almost always 6, but depends on cutout
        if cSlice > size(synImgData,3)
            disp('corner case')
            cSlice = size(synImgData,3);
        end
        % Adaptive value
        
        %Remove black slices
        for zz = 2:size(synImgData,3)
            if sum(sum(synImgData(:,:,zz))) == 0 %all black slice
                synImgData(:,:,zz) = synImgData(:,:,zz-1);
            end
        end
        
        % Coregister the images, center out
        [optimizer,metric] = imregconfig('monomodal');
        for zz = cSlice:-1:2
            synImgData(:,:,zz-1) = imregister(synImgData(:,:,zz-1),synImgData(:,:,zz),'translation',optimizer, metric);
        end
        
        for zz = cSlice:1:size(synImgData,3)-1
            synImgData(:,:,zz+1) = imregister(synImgData(:,:,zz+1),synImgData(:,:,zz),'translation',optimizer, metric);
        end
        
        val = synImgData(100-padd:100+padd,100-padd:100+padd,cSlice);
        minVal = 0;% prctile(val(:),5);
        maxVal = prctile(val(:),10);
        
        maxVal = min(maxVal,70);
        
        
        %regularize
        synImgData2(:,:,cSlice) = synImgData(:,:,cSlice) > minVal & synImgData(:,:,cSlice) < maxVal;
        
        for zz = cSlice:-1:2
            idx = find(synImgData2(:,:,zz) == 1);
            slice = synImgData(:,:,zz-1);
            sVal = slice(idx);
            synImgData2(:,:,zz-1) = imregister(synImgData(:,:,zz-1),synImgData(:,:,zz),'translation',optimizer, metric);
        end
        
        for zz = cSlice:1:size(synImgData,3)-1
            synImgData2(:,:,zz+1) = imregister(synImgData(:,:,zz+1),synImgData(:,:,zz),'translation',optimizer, metric);
        end
        
        
        %regularize
        synImgData2 = synImgData > minVal & synImgData < maxVal;
        
        s1 = [0 1 0; 1 1 1; 0 1 0];
        
        s2 = [0 0 1 0 0; 0 1 1 1 0; 1 1 1 1 1; 0 1 1 1 0; 0 0 1 0 0];
        
        s3 = [0 0 0 1 0 0 0; 0 0 1 1 1 0 0; 0 1 1 1 1 1 0; ...
            1 1 1 1 1 1 1; 0 1 1 1 1 1 0; 0 0 1 1 1 0 0; ...
            0 0 0 1 0 0 0];
        
        synImgData2 = imdilate(synImgData2, s2);
        synImgData2 = imerode(synImgData2, s2);
        
        bw = bwconncomp(synImgData2,6);
        mtx = labelmatrix(bw);
        
        % Robust version of connector value
        
        id = mtx(100-padd:100+padd,100-padd:100+padd,cSlice);
        idConn = mode(id(id>0));
        
        %Check for Perforated Synapse - assume 2 kinds
        id2 = id;
        id2(id == idConn) = 0;
        idConn2 = mode(id2(id2>0));
        sVal = sum(sum(mtx(:,:,cSlice) == idConn));
        sVal2 = sum(sum(mtx(:,:,cSlice) == idConn2));
        
        %idConn2:
        % Find centroid
        % Go +/- 20.  1600
        mitoCheck = zeros(size(id));
        mitoCheck(id == idConn2) = 1;
        [xIdx, yIdx]= find(mitoCheck>0);
        cMito = [round(mean(xIdx)), round(mean(yIdx))];
        xmin = max(cMito(1)-30, 1);
        xmax = min(cMito(1)+30, size(id,1));
        ymin = max(cMito(2)-30, 1);
        ymax = min(cMito(2)+30, size(id,1));
        
        mito = synImgData(xmin:xmax,ymin:ymax);
        mCount = sum(mito(:) < 150 & mito(:) > 80);
        if 0%sVal2/sVal > 0.5 && mCount < 600
            perfCount = perfCount+1;
            mtx(mtx~=idConn & mtx~=idConn2) = 0;
        else
            
            mtx(mtx~=idConn) = 0;
        end
        
        mtx(mtx>0) = 1;
        
        eeTotal = 0;
       
        
        if method == 1
            for j = 1:size(mtx,3)
                
                if plotFlag
                    hh = subplot(5,5,j);
                    jj = jet;
                    jj(1,:) = [0, 0, 0];
                    [hFront,hBack] = imoverlay(synImgData(:,:,j),mtx(:,:,j)*255,[0,255],[0,255],jj,0.5,hh);
                end
                slice = mtx(:,:,j);
                
                if sum(slice(:)) > 0
                    bwObj = bwconncomp(slice);
                    if plotFlag
                    end
                    for kk = 1:bwObj.NumObjects
                        if length(bwObj.PixelIdxList{kk}) >= 10
                            slice2 = zeros(size(mtx(:,:,j)));
                            slice2(bwObj.PixelIdxList{kk}) = 1;
                            
                            ee = regionprops(slice2,'Orientation', 'MajorAxisLength', ...
                                'MinorAxisLength', 'Eccentricity', 'Centroid','Solidity','Area');
                            eeTotal = ee.MajorAxisLength + eeTotal;
                            
                            if j > 0 %== cSlice
                                
                                phi = linspace(0,2*pi,50);
                                cosphi = cos(phi);
                                sinphi = sin(phi);
                                
                                xbar = ee.Centroid(1);
                                ybar = ee.Centroid(2);
                                
                                a = ee.MajorAxisLength/2;
                                b = ee.MinorAxisLength/2;
                                
                                theta = pi*ee.Orientation/180;
                                R = [ cos(theta)   sin(theta)
                                    -sin(theta)   cos(theta)];
                                
                                xy = [a*cosphi; b*sinphi];
                                xy = R*xy;
                                
                                x = xy(1,:) + xbar;
                                y = xy(2,:) + ybar;
                                
                                %fprintf('Compactness %f\n', ee.Solidity)
                                %fprintf('Ratio Metric:  %f...\n',ee.Area/aa);
                                %fprintf('Minor Axis:  %f...\n',ee.MinorAxisLength);
                                %disp('preout')
                                if plotFlag
                                    %disp('made it')
                                    hold on
                                    plot(x,y,'b','LineWidth',2);
                                    hold off
                                    
                                end
                                
                            end
                        end
                        
                    end
                end
            end
            sStrength(i) = eeTotal;
            
        end
        
        if plotFlag
            if saveFlag
                if i < 10
                    nn = ['00',num2str(i)];
                elseif i < 100
                    nn = ['0',num2str(i)];
                    
                else
                    nn = num2str(i);
                end
                set(gcf,'Color',[1 1 1]);
                set(gcf,'NextPlot','add');
                axes;
                h = title(sprintf('Synapse Number: %d.  Total Area:  %d', criticalIdx(i),round(sStrength(i))));
                set(gca,'Visible','off');
                set(h,'Visible','on');
                print(['criticalSyn_',nn,'.png'], '-dpng')
            else
                pause
            end
            
            close all
        end
    end
end
t = toc;

fprintf('Time Elapsed:  %d seconds\n', t);
