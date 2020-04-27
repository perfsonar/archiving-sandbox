def filter(event)
    paths = event.get("[result][paths]")
    if paths and paths.respond_to?('length') and paths.length() > 0 then
        #only look at first path for now, multipath is not this use case 
        hop_ips = []
        hop_asns = []
        path_mtu  = nil
        success_count = 0
        error_count = 0
        paths[0].each do |hop|
            #IP
            if hop["ip"] then
                hop_ips.push(hop["ip"])
                success_count += 1
            else
                error_count += 1
                next
            end
            
            #ASN
            if hop["as"] and hop["as"]["number"] then
                hop_asns.push(hop["as"]["number"])
            end
            
            #Path MTU
            begin
                if hop["mtu"] and (!path_mtu or hop["mtu"] < path_mtu) then
                    path_mtu = hop["mtu"]
                end
            rescue
                #ignore integer errors and similar
            end
        end
        
        #update event
        event.set("[@metadata][result][hop][count]", success_count + error_count)
        event.set("[@metadata][result][hop][success_count]", success_count)
        event.set("[@metadata][result][hop][error_count]", error_count)
        event.set("[@metadata][result][hop][ip]", hop_ips)
        event.set("[@metadata][result][hop][asn]", hop_asns)
        if path_mtu then
            event.set("[@metadata][result][mtu]", path_mtu)
        end
    end
    
    return [event]
end