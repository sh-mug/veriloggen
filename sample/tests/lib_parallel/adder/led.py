import sys
import os
import math

from veriloggen import *

try:
    log2 = math.log2
except:
    def log2(v):
        return math.log(v, 2)

def mkLed(numports=4):
    if log2(numports) % 1.0 != 0.0:
        raise ValueError('numports must be power of 2')
    
    m = Module('blinkled')
    clk = m.Input('CLK')
    rst = m.Input('RST')
    
    idata = [ m.Input('idata' + str(i), 32) for i in range(numports) ]
    ivalid = [ m.Input('ivalid' + str(i)) for i in range(numports) ]
    odata = m.OutputReg('odata', 32, initval=0)
    ovalid = m.OutputReg('ovalid', initval=0)

    par = lib.Parallel(m, 'par')
    pdata = idata
    pvalid = ivalid
    ndata = []
    nvalid = []
    
    for s in range( int(log2(numports)) ):
        for i in range( numports >> (s+1) ):
            td = m.TmpReg(32, initval=0)
            tv = m.TmpReg(initval=0)
            ndata.append(td)
            nvalid.append(tv)
            cond = AndList(pvalid[i*2], pvalid[i*2+1])
            par.add( tv(cond) )
            par.add( td(pdata[i*2] + pdata[i*2+1]), cond=cond )
        pdata = ndata
        pvalid = nvalid

    par.add( odata(pdata[-1]) )
    par.add( ovalid(pvalid[-1]) )
        
    par.make_always(clk, rst)

    return m

def mkTest():
    m = Module('test')

    # target instance
    led = mkLed()
    
    # copy paras and ports
    params = m.copy_params(led)
    ports = m.copy_sim_ports(led)

    clk = ports['CLK']
    rst = ports['RST']
    idata = [ p for k, p in sorted(ports.items(), key=lambda x:x[0]) if k.startswith('idata') ]
    ivalid = [ p for k, p in sorted(ports.items(), key=lambda x:x[0]) if k.startswith('ivalid') ]
    
    uut = m.Instance(led, 'uut',
                     params=m.connect_params(led),
                     ports=m.connect_ports(led))

    reset_stmt = []
    for d in idata:
        reset_stmt.append( d(0) )
    for v in ivalid:
        reset_stmt.append( v(0) )
    
    lib.simulation.setup_waveform(m, uut)
    lib.simulation.setup_clock(m, clk, hperiod=5)
    init = lib.simulation.setup_reset(m, rst, reset_stmt, period=100)

    nclk = lib.simulation.next_clock
    
    init.add(
        Delay(1000),
        nclk(clk),
        
        [ d(0) for d in idata ],
        [ v(0) for v in ivalid ],
        nclk(clk),
        
        [ d(i+1) for i, d in enumerate(idata) ],
        [ v(1) for v in ivalid ],
        nclk(clk),
        
        [ d(1) for d in idata ],
        [ v(0) for v in ivalid ],
        nclk(clk),
        
        [ d(i+10) for i, d in enumerate(idata) ],
        [ v(1) for v in ivalid ],
        nclk(clk),
        
        [ v(0) for v in ivalid ],
        [ nclk(clk) for _ in range(10) ],
        
        Systask('finish'),
    )

    return m
    
if __name__ == '__main__':
    test = mkTest()
    verilog = test.to_verilog('tmp.v')
    print(verilog)