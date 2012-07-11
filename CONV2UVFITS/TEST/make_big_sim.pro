; requires "corr_sim.pro" to be pre-compiled
pro make_big_sim
	dec = -60.0
;    for ha=3,2.0,0.5 do begin
    for ha=-2.0,2.0,0.5 do begin
        print,"Making sim for ha ",ha,", dec ",dec
        make_sim_data_complex,d,ha,dec

        ; write the output
        filename = string(ha,format='(%"simdat16_ha%0.2f.dat")')
        print,filename
        sig = stddev(abs(d[*,*,0]))
        reals = fix(round(float(d)*(8./(3*sig))))
        p = where(reals lt 0)
        reals[p] = reals[p]+32 ; create unsigned twos comp representation
        imags = fix(round(imaginary(d)*(8./(3*sig))))
        p = where(imags lt 0)
        imags[p] = imags[p]+32
        temp = uint(reals*32 AND ishft(31,5))+ uint(imags AND 31); this creates IDL uint type, which is 16 bit.
        openw,1,filename
        writeu,1,temp
        close,1

    endfor

	dec = -20.0
;    for ha=3,2.0,0.5 do begin
    for ha=-2.25,2.0,0.5 do begin
        print,"Making sim for ha ",ha,", dec ",dec
        make_sim_data_complex,d,ha,dec

        ; write the output
        filename = string(ha,format='(%"simdat16_ha%0.2f.dat")')
        print,filename
        sig = stddev(abs(d[*,*,0]))
        reals = fix(round(float(d)*(8./(3*sig))))
        p = where(reals lt 0)
        reals[p] = reals[p]+32 ; create unsigned twos comp representation
        imags = fix(round(imaginary(d)*(8./(3*sig))))
        p = where(imags lt 0)
        imags[p] = imags[p]+32
        temp = uint(reals*32 AND ishft(31,5))+ uint(imags AND 31); this creates IDL uint type, which is 16 bit.
        openw,1,filename
        writeu,1,temp
        close,1

    endfor
    
	dec = -40.0
    for ha=-2.1,2.0,0.5 do begin
        print,"Making sim for ha ",ha,", dec ",dec
        make_sim_data_complex,d,ha,dec

        ; write the output
        filename = string(ha,format='(%"simdat16_ha%0.2f.dat")')
        print,filename
        sig = stddev(abs(d[*,*,0]))
        reals = fix(round(float(d)*(8./(3*sig))))
        p = where(reals lt 0)
        reals[p] = reals[p]+32 ; create unsigned twos comp representation
        imags = fix(round(imaginary(d)*(8./(3*sig))))
        p = where(imags lt 0)
        imags[p] = imags[p]+32
        temp = uint(reals*32 AND ishft(31,5))+ uint(imags AND 31); this creates IDL uint type, which is 16 bit.
        openw,1,filename
        writeu,1,temp
        close,1

    endfor

end
