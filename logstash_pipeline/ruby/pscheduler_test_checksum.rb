require 'json'
require 'digest'

def to_json_c14n(obj)
    if(obj.is_a?(String)) then
        obj.to_json
    elsif(obj.is_a?(Numeric)) then
        raise RangeError if obj.is_a?(Float) && (obj.nan? || obj.infinite?)
        return "0" if obj.zero?
        num = obj
        if num < 0
          num, sign = -num, '-'
        end
        native_rep = "%.15E" % num
        decimal, exponential = native_rep.split('E')
        exp_val = exponential.to_i
        exponential = exp_val > 0 ? ('+' + exp_val.to_s) : exp_val.to_s

        integral, fractional = decimal.split('.')
        fractional = fractional.sub(/0+$/, '')  # Remove trailing zeros

        if exp_val > 0 && exp_val < 21
          while exp_val > 0
            integral += fractional.to_s[0] || '0'
            fractional = fractional.to_s[1..-1]
            exp_val -= 1
          end
          exponential = nil
        elsif exp_val == 0
          exponential = nil
        elsif exp_val < 0 && exp_val > -7
          # Small numbers are shown as 0.etc with e-6 as lower limit
          fractional, integral, exponential = integral + fractional.to_s, '0', nil
          fractional = ("0" * (-exp_val - 1)) + fractional
        end

        fractional = nil if fractional.to_s.empty?
        sign.to_s + integral + (fractional ? ".#{fractional}" : '') + (exponential ? "e#{exponential}" : '')
    elsif(obj.is_a?(Array)) then
        '[' + obj.map{ |v| to_json_c14n(v)}.join(',') + ']'
    elsif(obj.is_a?(Hash)) then
        "{" + obj.
          keys.
          sort_by {|k| k.encode(Encoding::UTF_16)}.
          map {|k| to_json_c14n(k) + ':' + to_json_c14n(obj[k])}
          .join(',') +
        '}'
    else
        obj.to_json
    end
end

def filter(event)
    normalized_obj = {}
    normalized_obj["test"] = event.get("test")
    normalized_obj["observer_ip"] = event.get("[meta][observer][ip]")
    normalized_obj["tool"] = event.get("[pscheduler][tool]")
    digest = Digest::SHA256.hexdigest to_json_c14n(normalized_obj)
    event.set("[pscheduler][test_checksum]", digest)
    
    return [event]
end

#test = {
#    "foo" => "bar",
#    "a" => {
#        "d" => [{"z"=>26, "y"=>25}, "g", "f"],
#        "b" => "c"
#    }
#}
#puts to_json_c14n(test)