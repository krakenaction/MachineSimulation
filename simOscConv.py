from modMechSim import *

vfdA=VFD('first vfd',{'off':0,'high':60,'mid':45,'low':30,'highrev':-60,'midrev':-45,'lowrev':-30})
motorA=ACMotor('dayton conveyor motor',230,60,1700)
gearboxA=GearChain('dayton gearhead',80)
sprocketA=ConveyorSprocket('uhmw sprocket',4)
beltA=ConveyorBelt('12in brown belt')

conveyorA=MotionChain('depal conveyor',vfdA)
conveyorA.addChainComponent(motorA)
conveyorA.addChainComponent(gearboxA)
conveyorA.addChainComponent(sprocketA)
conveyorA.addChainComponent(beltA)

conveyorA.addMode('oscforward','high','maxdistance',{'modeoutput','modetime'},'oscendpause')
conveyorA.addMode('oscendpause','off','pausetimelimit',{'modeoutput','modetime'},'oscreverse')
conveyorA.addMode('oscreverse','midrev','home',{'modeoutput','modetime','cycleinc','allcomponents'},'oschomepause')
conveyorA.addMode('oschomepause','off','pausetimelimit',{'modeoutput','modetime'},'oscforward')

conveyorA.addState('maxdistance','>=',beltA,72)
conveyorA.addState('pausetimelimit','modetime',conveyorA,3)
conveyorA.addState('home','<=',beltA,0)

conveyorA.printChainSetup(True)

depalsim = Simulation('depal conveyor osc sim')
depalsim.addChain(conveyorA)
depalsim.addOpShift('runmode',[conveyorA.name],['oscforward'],['convcyclectr'],['off'])
depalsim.initMode = 'runmode'
depalsim.addSensor('convcyclectr','cycle>=',conveyorA,5)
depalsim.maxtime = 300
depalsim.printSimSetup()


depalsim.runSim()