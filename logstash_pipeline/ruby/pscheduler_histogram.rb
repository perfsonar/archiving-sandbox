
##
# Percentile: Used by histogram class to calculate percentiles using the NIST
# algorithm (http://www.itl.nist.gov/div898/handbook/prc/section2/prc252.htm)
class Percentile
    def initialize(percentile, sample_size)
        @value = nil
        @is_calculated = false
        @percentile = percentile
        @sample_size = sample_size
        @n = (@percentile/100.0)*(sample_size + 1)
        @k = @n.floor
        @d = @n - @k
        
        if percentile == 50 then
            @key = "median"
        else
            @key = "p_" + percentile.to_s
        end
    end
    
    def key
        @key
    end
    
    def value
        @value
    end
    
    def k
        @k
    end
    
    def calculated?
        @is_calculated
    end
  
    def findvalue(count, hist_value)
        if @value then
            @value += (@d * (hist_value - @value))
            @is_calculated = true
        elsif @k == 0 then
            @value = hist_value
            @is_calculated = true
        elsif count >= @sample_size and @k >= @sample_size then
            @value = hist_value
            @is_calculated = true
        elsif (@k + @d) < count then
            @value = hist_value
            @is_calculated = true
        else
            @value = hist_value
        end
    end
end

##
# Histogram class used to calculate common histogram metrics
class Histogram
    
    def initialize(hist_dict, quantiles)
        @hist_dict = hist_dict
        if quantiles then
            @quantiles = quantiles
        else
            @quantiles = [25, 50, 75, 95]
        end
    end
    
    def get_stats()
        #pass one: mode, mean and sample size
        if !@hist_dict then
            return {}
        end
        #initialize stats with histogram object understood by elastic
        stats = {
            "histogram" => {
                "values" => [],
                "counts" => [],
            }
        }
        
        mean_num = 0
        sample_size = 0
        @hist_dict.keys.sort_by{ |_k, _v| _k.to_f }.each() do |k|
            #only can do statistics for histograms with numeric buckets
            begin
                k_val = k.to_f
                count_val = @hist_dict[k].to_i
            rescue
                return {}
            end
            
            #Update the raw histogram - this is understood by elastic
            stats['histogram']['values'].push(k_val)
            stats['histogram']['counts'].push(count_val)
            
            # update calculation values
            if !stats.key?('mode') or @hist_dict[k] > @hist_dict[stats['mode'][0]] then
               stats['mode'] = [ k ]
            elsif @hist_dict[k] == @hist_dict[stats['mode'][0]] then
                stats['mode'].push(k)
            end
            mean_num += (k_val * @hist_dict[k])
            sample_size += @hist_dict[k]
        end
        
        if sample_size == 0 then
            return {}
        end
        stats['mean'] = (mean_num/(1.0*sample_size))
        
        #sort items. make sure sort as numbers not strings
        sorted_hist = @hist_dict.keys.sort_by{ |_k, _v| _k.to_f }.map { |key| [key.to_f, @hist_dict[key]] }
        #make mode floats.
        stats['mode'] = stats['mode'].map { |x| x.to_f }
        #get min and max
        stats['min'] = sorted_hist[0][0].to_f
        stats['max'] = sorted_hist[sorted_hist.length()-1][0].to_f
        
        #pass two: get quantiles, variance, and std deviation
        stddev = 0
        percentiles = []
        @quantiles.each() do |q|
            percentiles.push(Percentile.new(q, sample_size))
        end
        percentile = percentiles.shift()
        curr_count = 0
        sorted_hist.each() do |hist_item|
            #stddev/variance
            stddev += (((hist_item[0].to_f - stats['mean']) ** 2)*hist_item[1])
            #quantiles
            curr_count += hist_item[1]
            while percentile and curr_count >= percentile.k
                percentile.findvalue(curr_count, hist_item[0].to_f)
                #some percentiles require next item in list, so may have to wait until next iteration
                if percentile.calculated? then
                    #calculated so add to dict
                    stats[percentile.key] = percentile.value
                else
                    #unable to calculate this pass, so break loop
                    break
                end
                
                #get next percentile
                if percentiles.length() > 0 then
                    percentile = percentiles.shift()
                else
                    percentile = nil
                end
            end
        end
        
        #set standard deviation
        stats['variance'] = stddev/sample_size
        stats['stddev'] = Math.sqrt(stats['variance'])    
        return stats
    end
end

def register(params)
    @source = params["source"]
    @target = params["target"]
    @quantiles = params["quantiles"] #optional array of ints, sane default in class
end

def filter(event)
    #get the histogram object
    if !@source then
        #throw error since always need this
        event.tag("histogram_source_field_not_specified")
        return [event]
    end
    hist = event.get(@source)
    if !hist then
        #just move along
        return [event]
    end
    
    #check the target field param
    if !@target then
        #throw error since always need this
        event.tag("histogram_target_field_not_specified")
        return [event]
    end
    #make sure we have square brackets around target
    @target = "[" + @target.sub(/^\[/,"").sub(/\]$/,"") + "]"
    
    #calculate the stats
    stats = Histogram.new(hist, @quantiles).get_stats()
    #stuff all the results in target object
    stats.keys.each() { |k| event.set("#{@target}[#{k}]", stats[k]) }
    
    return [event]
end

#puts Histogram.new({"1"=>1, "2" => 1, "3" => 1}).get_stats()