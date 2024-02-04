from math import pi, floor, isclose
from statistics import mean

digits = 2

def listify(*inputs):
    if isinstance(inputs,str):
        return [input]
    else:
        return [input if isinstance(input,list) else [input] for input in inputs]

def prec(num):
    if isinstance(num,list):
        return [round(entry,digits) for entry in num]
    else:
        return round(num,digits)

def stateCheck(crit,comp,val):
    match crit:
        case '>=':
            return comp.output >= val
        case '<=':
            return comp.output <= val
        case '==':
            return comp.output == val
        case 'setting=':
            return comp.setting == val
        case 'change>=':
            return comp.change >= val
        case 'change<=':
            return comp.change <= val
        case 'rpm>=':
            return comp.rpm >= val
        case 'rpm<=':
            return comp.rpm >= val
        case 'modetime':
            return comp.modetime >= val
        case 'cycle>=':
            return comp.cyclecount >= val

class MotionComponent:
    def __init__(self, name, imeas, omeas, eff=100) -> None:
        self.name = name 
        self.inputmeas = imeas
        self.outputmeas = omeas
        self.output = 0
        self.change = 0
        self.sampled = False
        self.active = False
        self.settable = False
        self.efficiency = eff

    def printComponentSetup(self):
        print('    ',self.name,'converting',self.inputmeas,'to',self.outputmeas)
        if self.settable:
            print('      settings:',self.settings)
        if self.sampled:
            print('      using sample data',self.samplespeeds.items())
            
    def printComponentState(self):
        tail = ''
        if self.settable:
            tail ='setting '+self.setting
        print('    ',self.name,'change',prec(self.change),self.outputmeas,'to',prec(self.output),self.outputmeas,tail)
        
class SettableComponent(MotionComponent):
    def __init__(self, name, imeas, omeas) -> None:
        super().__init__(name, imeas, omeas)
        self.settings = set()
        self.settingtypes = {}
        self.settingvalues = {}

    def addSetting(self, setting, val, speedQ=False):
        self.settings.add(setting)
        self.settingtypes[setting] = speedQ
        self.settingvalues[setting] = val
        self.settable = True

    def iterateBySetting(self,dt):
        if self.settingtypes[self.setting]:
            self.change = self.settingvalues[self.setting]*dt
            self.output += self.change
        else:
            self.change = self.settingvalues[self.setting]-self.output
            self.output = self.settingvalues[self.setting]

class PowerSwitch(SettableComponent):
    def __init__(self, name, volts, Hz) -> None:
        super().__init__(name, 'setting', 'Hz')
        self.addSetting('on',Hz)
        self.addSetting('off',0)
        self.specVoltage = volts

class VFD(SettableComponent):
    def __init__(self, name, outputDict) -> None:
        super().__init__(name, 'setting', 'Hz')
        for setting, value in outputDict.items():
            self.addSetting(setting,value)

class SampledComponent(MotionComponent):
    def __init__(self, name, imeas, omeas) -> None:
        super().__init__(name, imeas, omeas)
        self.settings = set()
        self.sampleData = {}
        self.sampleSwitch = {}
        self.sampleSpeeds = {}
        self.sampleRanges = {}

    def addSampleSet(self, setting, data, startpoint, endpoint):
        self.settings.add(setting)
        self.sampleData[setting] = data
        self.sampleSwitch[setting] = True
        self.sampleSpeeds[setting] = mean([a/b for a,b in data])
        self.sampleRanges[setting] = [startpoint,endpoint]
        self.sampled = True

    def setSampledState(self, setting, state):
        self.sampleSwitch[setting] = state

    def withinSampleRange(self, setting):
        a,b = self.sampleRanges[setting]
        return self.output >= a and (self.output <= b or b < 0)
    
    def iterateBySample(self,dt):
        self.change = self.sampleSpeeds[self.setting]*dt
        if self.reverse:
                self.change = -self.change
        self.output += self.change

class ACMotor(SampledComponent):
    def __init__(self, name, volts, Hz, nameplateRPM) -> None:
        super().__init__(name, 'Hz', 'rotations')
        self.specVoltage = volts
        self.specFrequency = Hz
        self.specRPM = nameplateRPM

    def iterateByDesign(self,dt):
        self.rpm=self.inputObj.output/self.specFrequency*self.specRPM
        self.change = self.rpm/60*dt
        self.output += self.change

class GearChain(SampledComponent):
    def __init__(self, name, reduction) -> None:
        super().__init__(name, 'rotations', 'rotations')
        self.gearRatio = reduction

    def iterateByDesign(self,dt):
        self.change = self.inputObj.change/self.gearRatio
        self.output += self.change
        self.rpm = self.change/dt*60

class ConveyorSprocket(SampledComponent):
    def __init__(self, name, Din) -> None:
        super().__init__(name, 'rotations', 'in')
        self.radius = Din/2

    def iterateByDesign(self,dt):
        self.change = 2*pi*self.radius*self.inputObj.change
        self.output += self.change

class WoundBeltDrum(SampledComponent):
    def __init__(self, name, Din, Tin, num) -> None:
        super().__init__(name, 'rotations', 'in')
        self.baseradius = Din/2
        self.beltthickness = Tin
        self.beltcount = num
        self.windingUp = True
        self.rotations = 0
        self.radius = self.baseradius
        self.rpm = 0

    def iterateByDesign(self,dt):
        self.rotations = self.rotations + self.inputObj.change
        self.change = 2*pi*self.radius*self.inputObj.change
        self.output += self.change
        self.rpm = self.inputObj.change/dt*60
        self.radius = self.baseradius + self.beltthickness*self.beltcount*abs(self.rotations)
        if self.rotations < 0:
            self.windingUp = True

class ConveyorBelt(SampledComponent):
    def __init__(self, name) -> None:
        super().__init__(name, 'in', 'in')

    def iterateByDesign(self,dt):
        self.change = self.inputObj.change
        self.output += self.change

class MotionChain(SampledComponent):
    def __init__(self, name, source) -> None:
        super().__init__(name, source.inputmeas, source.outputmeas)
        if source.inputmeas != 'setting':
            print("mismatching measures",self.name,source.name)
            return
        self.cyclecount = 0
        self.modeoutput = 0
        self.modetime = 0
        self.chain = [source]
        self.settings = source.settings
        self.mode = 'offmode'
        self.modeActions = {'offmode':[['',[],'']]}
        #            {'mode name:[[state name applicable during this mode,{props to change/reset},newmodename to switch to given state]]}
        self.modeSettings = {'offmode':'off'}
                            #  {'mode name:switch to setting}
        self.states = {}
        #               {'statenamename':[['type'],[all obj],[values]]}
        self.product = []
        self.prodInputCont = False
        self.prodOutputCont = False

    def addMode(self,modeName,settingname,statelist,propchangelist,newmodelist):
        if modeName in self.modeActions.keys():
            print('mode',modeName,'already exists in',self.name)
            return
        statelist,propchangelist,newmodelist = listify(statelist,propchangelist,newmodelist)
        self.modeActions[modeName] = list(zip(statelist,propchangelist,newmodelist))
        self.modeSettings[modeName] = settingname

    def addState(self,statename,typeslist, objectslist, valueslist):
        if statename in self.states.keys():
            print('state',statename,'already exists in',self.name)
            return
        typeslist,objectslist,valueslist = listify(typeslist,objectslist,valueslist)
        self.states[statename] = list(zip(typeslist,objectslist,valueslist))

    def addChainComponent(self, component):
        inputcomponent = self.chain[-1]
        if inputcomponent.outputmeas != component.inputmeas:
            print("mismatching measures",inputcomponent.name,component.name)
            return
        component.inputObj = inputcomponent
        self.chain.append(component)
        self.outputmeas = component.outputmeas

    def switchSetting(self,setting):
        if setting in self.settings:
            self.setting = setting
            self.chain[0].setting = setting
            print('switched',self.name,'to setting:',self.setting)
    
    def switchMode(self,modename):
        if not(modename in self.modeActions.keys()):
            print('mode',modename,'does not exist in',self.name)
            return
        self.mode = modename
        setting = self.modeSettings[modename]
        self.switchSetting(setting)
        print('switched',self.name,'to mode:',setting)

    def iterateChain(self,dt):
        if self.setting in self.settings:
            for comp in self.chain:
                if comp.settable:
                    comp.iterateBySetting(dt)
                elif comp.sampled:
                    comp.iterateBySample(dt)
                else:
                    comp.iterateByDesign(dt)
            self.change = self.chain[-1].output-self.output
            self.output = self.chain[-1].output
            self.modetime += dt
            self.checkStates()

    def checkStates(self):
        for modetrio in self.modeActions[self.mode]:
            if len(modetrio) > 0:
                for crit,comp,val in self.states[modetrio[0]]:
                    if stateCheck(crit,comp,val):
                        print('chain state trigger:',comp.name,'is',crit,'than',val)
                        self.resetProps(modetrio[1])
                        self.switchMode(modetrio[2])
                        return True
        return False
    
    def resetProps(self,propnames):
        for name in propnames:
            match name:
                case 'cycleinc':
                    self.cyclecount += 1
                case 'cyclecount':
                    self.cyclecount = 0
                case 'modeoutput':
                    self.modeoutput = 0
                case 'modetime':
                    self.modetime = 0
                case 'output':
                    self.output = 0
                case 'allcomponents':
                    self.resetComponents()
                case _:
                    print('property',name,'does not exist in',self.name)

    def resetComponents(self):
        self.output = 0
        for comp in self.chain:
            comp.output = 0

    def printChainSetup(self,alsocomps=False):
        print('  chain:',self.name,'converting',self.inputmeas,'to',self.outputmeas)
        print('  -with modes',self.modeActions.keys())
        print('  -and state triggers:',self.states.keys())
        if alsocomps:
            for comp in self.chain:
                comp.printComponentSetup()

    def printChainState(self,alsocomps=False):
        print('  motion chain',self.name,'setting',self.setting)
        if alsocomps:
            for comp in self.chain:
                comp.printComponentState()
        print('  ',self.name,'cycles:',self.cyclecount,'output:',prec(self.output),self.outputmeas,'mode time:',prec(self.modetime))

class Simulation():
    def __init__(self,name) -> None:
        self.name = name
        self.deltaT = 0.1
        self.duration = 0
        self.maxtime = 5
        self.updatetime = 2
        self.updateaccum = 0
        self.cyclecount = 0
        self.chains = {}
        self.opMode = 'off'
        self.initMode = ''
        self.opShifts = {'off':[]}
        self.sensorSets = {}
        self.sensors = {}
        self.product = []

    def addChain(self,chain):
        self.chains[chain.name] = chain
        self.opShifts['off'].append([chain.name,'off'])

    def addOpShift(self,shiftname,chainnameslist,modeslist,sensorlist,newmodelist):
        if shiftname in self.opShifts.keys():
            print('op',shiftname,'already exists in',self.name)
            return
        self.opShifts[shiftname] = list(zip(chainnameslist,modeslist))
        sensorlist,newmodelist = listify(sensorlist,newmodelist)
        self.sensorSets[shiftname] = list(zip(sensorlist,newmodelist))

    def addSensor(self,sensorname,typeslist, objectslist, valueslist):
        if sensorname in self.sensors.keys():
            print('sensor',sensorname,'already exists in',self.name)
            return
        typeslist,objectslist,valueslist = listify(typeslist,objectslist,valueslist)
        self.sensors[sensorname] = list(zip(typeslist,objectslist,valueslist))

    def shiftChains(self,shiftname):
        self.opMode = shiftname
        for name,mode in self.opShifts[shiftname]:
            self.chains[name].switchMode(mode)

    def iterateSim(self):
        self.duration += self.deltaT
        self.updateaccum += self.deltaT
        for chain in self.chains.values():
            chain.iterateChain(self.deltaT)
        if self.updateaccum >= self.updatetime or isclose(self.updateaccum,self.updatetime,rel_tol=0.00001):
            self.printSimState()
            self.updateaccum = 0

    def runSim(self):
        self.duration = 0
        self.updateaccum = 0
        if self.deltaT > 0 and self.maxtime > 0:
            print(self.name,'simulation starting:')
            self.shiftChains(self.initMode)
            while self.duration < self.maxtime and self.opMode != 'off':
                self.iterateSim()
                self.checkSensors()
            print(self.name,'simulation finished:')
            self.printSimState()     

    def checkSensors(self):
        for sensorname,newmode in self.sensorSets[self.opMode]:
            trip = True
            for checktype,comp,val in self.sensors[sensorname]:
                trip = stateCheck(checktype,comp,val)
                if not trip:
                    break
            if trip:
                self.shiftChains(newmode)
                break
                
    def printSimSetup(self,alsocomps=False):
        print(self.name,'setup with',len(self.chains),'motion chains using deltaT of',self.deltaT,'sec and a max run time of',self.maxtime)
        for chain in self.chains.values():
            chain.printChainSetup(alsocomps)

    def printSimState(self,alsocomps=False):
        print(self.name,prec(self.duration),'sec total')
        for chain in self.chains.values():
            chain.printChainState(alsocomps)

class productHandler():
    def __init__(self) -> None:
        self.prodFixedInBool = False
        self.prodFixedOutBool = False
        self.prodVariableProgressBool = False
        self.product = []

    def addFixedInput(self,productBatchesList):
        self.prodFixedInBool = True
        self.prodFixedInput = productBatchesList
        
    def addFixedOutput(self,productBatchesList):
        self.prodFixedOutBool = True
        self.prodFixedOutput = productBatchesList

    def addVariableProgress(self,packingRatio,ordinateDims,conveyorwidths):
        self.prodVariableProgressBool = True
        self.packRatio = packingRatio
        self.progOrds = ordinateDims
        self.progWidths = conveyorwidths

    