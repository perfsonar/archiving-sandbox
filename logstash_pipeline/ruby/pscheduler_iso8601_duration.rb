def duration_to_seconds(duration_string)
    if !duration_string then
        return
    end
    
    #regex to match duration and break into named parts
    duration = /(?x)
        ^
        (?:(?<repeats>R(?<repetitions>[0-9]+)?))?
        P
        (?:(?<years>[0-9]+)Y)?
        (?:(?<months>[0-9]+)M)?
        (?:(?<days>[0-9]+)D)?
        (?:T
            (?:(?<hours>[0-9]+)H)?
            (?:(?<minutes>[0-9]+)M)?
            (?:(?<seconds>[0-9]+(?:\.([0-9]+))?)S)?
        )?
        $
    /.match(duration_string)
    
    #skip out if not valid duration or has ambiguous time values
    if !duration or duration[:repeats] or duration[:months] or duration[:years] then
        return
    end
    
    #time for math
    total_seconds = 0.0
    total_seconds += duration[:seconds] ? duration[:seconds].to_f : 0
    total_seconds += duration[:minutes] ? duration[:minutes].to_f * 60 : 0
    total_seconds += duration[:hours] ? duration[:hours].to_f * 3600 : 0
    total_seconds += duration[:days] ? duration[:days].to_f * 86400 : 0
    
    return total_seconds
end

def register(params)
    @fields = params["fields"]
end

def filter(event)
    if !@fields then
        return
    end
    
    @fields.each do |field|
        v = event.get(field)
        secs = duration_to_seconds(v)
        if secs then
            event.set(field, secs)
        end
    end
    
    return [event]
end
