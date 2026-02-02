from Extension import *
from Allocations import *
from collections import defaultdict, deque

def validate_inputs(vehicle_capacities, five_person_groups, six_person_groups):
    if not all(isinstance(cap, int) and cap >= 0 for cap in vehicle_capacities):
        raise ValueError("Vehicle capacities must be a list of non-negative integers.")
    if not isinstance(five_person_groups, int) or five_person_groups < 0:
        raise ValueError("Five-person groups must be a non-negative integer.")
    if not isinstance(six_person_groups, int) or six_person_groups < 0:
        raise ValueError("Six-person groups must be a non-negative integer.")
def alltogether(combos,allist,damage):
    i=zip(combos,allist,damage)
    out=[]
    for elem in enumerate(i):
        out.append(elem[1])
    twos=[]
    threes=[]
    fours=[]
    fives=[]
    sixes=[]
    sevens=[]
    for item in out:
        if len(item[0])==2:
            twos.append(item)
        if len(item[0])==3:
            threes.append(item)
        if len(item[0])==4:
            fours.append(item)
        if len(item[0])==5:
            fives.append(item)
        if len(item[0])==6:
            sixes.append(item)
    return twos,threes,fours,fives,sixes,sevens

def compute_ranges(people):
    final=[]
    counter1=0
    people1=people
    final1=[]
    while people1>=0:
        if people1%6==0:
            final1.append(counter1+(people1//6))
        counter1+=1
        people1-=5
    counter2=0
    people2=people
    final2=[]
    while people2>=0:
        if people2%6==0:
            final2.append(counter2+(people2//6))
        counter2+=1
        people2-=7
    if final1:
        final.append([min(final1),max(final1)])
    else:
        final.append([])
    if final2:
        final.append([min(final2),max(final2)])
    else:
        final.append([])
    return final

def compute_matrices(people,crews):
    pers5=-1*people+6*crews
    pers6=people-5*crews
    if pers5>=0 and pers6>=0 and isinstance(pers5,int) and isinstance(pers6,int):
        return pers5,pers6,0
    pers7=people-6*crews
    pers6n=-1*people+7*crews
    if pers7>=0 and pers6n>=0 and isinstance(pers7,int) and isinstance(pers6n,int):
        return 0,pers6n,pers7
    return []

def harm(combos,allocations):
    out=[]
    for combo in combos:
        running=0
        for vehicle in combo:
            running+=sum(allocations[vehicle-1])
        out.append(running)
    return out

def combosSum(combos,allocations,shortfall):
    out=shortfall.copy()
    for combo in combos:
        for vehicle in combo:
            out[0]+=allocations[vehicle-1][0]
            out[1]+=allocations[vehicle-1][1]
    return out

def unused(allocations,combos):
    indeces=list(range(len(allocations)))
    unused=[]
    used=[]
    for combo in combos:
        for index in combo:
            used.append(index)
    for elem in indeces:
        if elem+1 not in used:
            unused.append(elem+1)
    return unused

def unused1(sizes, combos):
    usable = []
    for elem in combos:
        for i in elem:
            usable.append(i)
    for item in usable:
        sizes.remove(item)
    return sizes

def nonzero(remainders,vehicles):
    rem_af=[]
    veh_af=[]
    for elem in range(len(remainders)):
        if remainders[elem]!=0:
            rem_af.append(remainders[elem])
            veh_af.append(vehicles[elem])
    return rem_af, veh_af

def allone(combos):
    out=[]
    for elem in combos:
        for item in elem:
            out.append(item)
    return out
def oppallone(allone,vehlist):
    for x in allone:
        vehlist.remove(x)
    return vehlist
def sumAll(combos,vehlist):
    summ=0
    for x in combos:
        summ=0
        for m in x:
            summ+=m
            vehlist.remove(m)
        if summ!=0:
            vehlist.append(summ)
    return vehlist
def person_calc(combos,sizes):
    pers_out=[]
    for elem in combos:
        each=[]
        for i in elem:
            each.append(sizes[i-1])
        pers_out.append(each)
    return pers_out

def quant(unused_veh):
    look=list(set(unused_veh))
    look.sort()
    paired=[]
    for elem in look:
        paired.append([unused_veh.count(elem),elem])
    return paired

def restore_order(original, shuffled, list_of_lists, list_of_ints):

    index_map = defaultdict(deque)
    for i, value in enumerate(shuffled):
        index_map[value].append(i)

    sorted_indices = [index_map[value].popleft() for value in original]

    restored_shuffled = [shuffled[i] for i in sorted_indices]
    restored_list_of_lists = [list_of_lists[i] for i in sorted_indices]
    restored_list_of_ints = [list_of_ints[i] for i in sorted_indices]

    return restored_shuffled, restored_list_of_lists, restored_list_of_ints

def combine(space, shortfall, indices, backup_size=5):
    paired = list(zip(space, indices))
    paired.sort(key=lambda t: t[0], reverse=True)
    space, indices = map(list, zip(*paired)) if paired else ([], [])

    if sum(space) < backup_size * shortfall[0] + 6 * shortfall[1]:
        return None, None, None

    six = shortfall[1]
    backup = shortfall[0]
    used=set()
    combos = []
    init = []
    actual = []

    for m in range(len(space) - 2, -1, -1):
        if six == 0:
            break
        if m in used:
            continue

        for n in range(len(space) - 1, m, -1):
            if six == 0:
                break
            if n in used:
                continue

            if space[m] + space[n] >= 6 and m not in used and n not in used:
                used.add(m)
                used.add(n)
                combos.append([indices[m], indices[n]])
                six -= 1
                init.append([0, 1])
                actual.append([space[m],space[n]])

                if backup == 0 and six == 0:
                    return combos, init, actual
    for m in range(len(space) - 2, -1, -1):
        if backup == 0:
            break
        if m in used:
            continue
        for n in range(len(space) - 1, m, -1):
            if backup == 0:
                break
            if n in used:
                continue

            if space[m] + space[n] >= 5 and m not in used and n not in used:
                used.add(m)
                used.add(n)
                combos.append([indices[m], indices[n]])
                backup -= 1
                init.append([1, 0])
                actual.append([space[m],space[n]])

                if backup == 0 and six == 0:
                    return combos, init, actual

    return None, None, None

def sort_by_sum(combos, sorted_spaces, listing, actualCombos, one_based=False):
    if not combos:
        return [], [], []

    offset = 1 if one_based else 0

    paired = list(zip(combos, listing, actualCombos))
    paired.sort(key=lambda p: sum(sorted_spaces[idx - offset] for idx in p[0]))

    sorted_combos, sorted_listing, sorted_actual = zip(*paired)
    return list(sorted_combos), list(sorted_listing), list(sorted_actual)


def cleanup(combos, sorted_spaces, listing):
    size4, size3, other = [], [], []
    init4, init3, init_other = [], [], []
    size2, init2, actual2  = [], [], []
    size5, init5, actual5  = [], [], []
    actualCombos, actual4, actual3 = [],[],[]

    for i in range(len(combos)):
        inner=[]
        for j in range(len(combos[i])):
            combos[i][j]-=1
            inner.append(sorted_spaces[combos[i][j]])
        actualCombos.append(inner)

    for c, l, ac in zip(combos, listing, actualCombos):
        if len(c) == 5:
            size5.append(c); init5.append(l); actual5.append(ac)
        elif len(c) == 4:
            size4.append(c); init4.append(l); actual4.append(ac)
        elif len(c) == 3:
            size3.append(c); init3.append(l); actual3.append(ac)
        elif len(c) == 2:
            size2.append(c); init2.append(l); actual2.append(ac)
        else:
            other.append(c); init_other.append(l)

    size5, init5, actual5 = sort_by_sum(size5, sorted_spaces, init5, actual5)
    size4, init4, actual4 = sort_by_sum(size4, sorted_spaces, init4, actual4)
    size3, init3, actual3 = sort_by_sum(size3, sorted_spaces, init3, actual3)
    size2, init2, actual2 = sort_by_sum(size2, sorted_spaces, init2, actual2)
    new3, new3init, new3actual = [],[],[]
    used4,used3,used5 = set(),set(),set()
    progressFlag = False
    if size4 and size3:
        for m in range(len(size4)):
            if m in used4:
                continue
            for n in range(len(size3)):
                if n in used3 or m in used4:
                    continue
                total5s, total6s = init4[m][0]+init3[n][0],init4[m][1]+init3[n][1]
                placedFlag = False
                for a in range(len(size3[n])):
                    if placedFlag:
                        break
                    for b in range(0,len(size4[m])-1):
                        if placedFlag:
                            break
                        for c in range(b+1,len(size4[m])):
                            if placedFlag:
                                break
                            placed6s = min((actual4[m][c]+actual4[m][b]+actual3[n][a])//6,total6s)
                            placed5s = min((actual4[m][c]+actual4[m][b]+actual3[n][a]-6*placed6s)//5,total5s)
                            remaining = [total5s-placed5s,total6s-placed6s]
                            spacesL, indL = actual4[m].copy(), size4[m].copy()
                            spacesL.pop(c); indL.pop(c); spacesL.pop(b); indL.pop(b)
                            spacesR, indR = actual3[n].copy(), size3[n].copy()
                            spacesR.pop(a); indR.pop(a)
                            spaces, ind = spacesL+spacesR, indL+indR
                            comb, init, new2 = combine(spaces,remaining,ind)
                            if comb and m not in used4 and n not in used3:
                                new3.append([size4[m][b],size4[m][c],size3[n][a]])
                                new3actual.append([actual4[m][b],actual4[m][c],actual3[n][a]])
                                used3.add(n);used4.add(m)
                                new3init.append([placed5s,placed6s])
                                size3[n]=[]; init3[n]=[];size4[m]=[];init4[m]=[];actual3[n]=[];actual4[m]=[]
                                size2.extend(comb); init2.extend(init); actual2.extend(new2)
                                placedFlag, progressFlag = True, True
        size3.extend(new3); init3.extend(new3init); actual3.extend(new3actual)
        packed3 = [(s,i,a) for s,i,a in zip(size3, init3, actual3) if s]
        packed4 = [(s,i,a) for s,i,a in zip(size4, init4, actual4) if s]
        size3, init3, actual3 = (map(list, zip(*packed3)) if packed3 else ([], [], []))
        size4, init4, actual4 = (map(list, zip(*packed4)) if packed4 else ([], [], []))
    new3, new3init, new3actual = [],[],[]
    used3.clear()
    if size5 and size3:
        for m in range(len(size5)):
            if m in used5:
                continue
            for n in range(len(size3)):
                if n in used3 or m in used5:
                    continue
                total5s, total6s = init5[m][0]+init3[n][0],init5[m][1]+init3[n][1]
                placedFlag = False
                for a in range(len(size5[m])):
                    if placedFlag:
                        break
                    for b in range(len(size3[n])):
                        if placedFlag:
                            break
                        for c in range(0,len(size5[m])-1):
                            if placedFlag:
                                break
                            if c==a:
                                continue
                            for d in range(c+1,len(size5[m])):
                                if placedFlag:
                                    break
                                if d==a:
                                    continue
                                for e in range(len(size3[n])):
                                    if placedFlag:
                                        break
                                    if e==b:
                                        continue
                                    otherInd = 3 - b - e

                                    the2 = actual5[m][a] + actual3[n][b]
                                    first3 = actual5[m][c] + actual5[m][d] + actual3[n][e]

                                    rem5 = [i for i in range(len(actual5[m])) if i not in (a, c, d)]
                                    second3 = actual3[n][otherInd] + sum(actual5[m][i] for i in rem5)

                                    the2actual = [actual5[m][a]]+[actual3[n][b]]
                                    first3actual = [actual5[m][c]]+[actual5[m][d]]+[actual3[n][e]]
                                    second3actual = [actual3[n][otherInd]] + [actual5[m][i] for i in rem5]

                                    new2 = [size5[m][a]]+[size3[n][b]]
                                    new31 = [size5[m][c]]+[size5[m][d]]+[size3[n][e]]
                                    new32 = [size3[n][otherInd]] + [size5[m][i] for i in rem5]

                                    placed6s2s = min(the2//6,total6s)
                                    placed5s2s = min((the2-6*placed6s2s)//5,total5s)
                                    remaining = [total5s-placed5s2s,total6s-placed6s2s]

                                    placed6sfirst = min(first3//6,remaining[1])
                                    placed5sfirst = min((first3-6*placed6sfirst)//5,remaining[0])
                                    remaining1 = [remaining[0]-placed5sfirst,remaining[1]-placed6sfirst]

                                    placed6ssecond = min(second3//6,remaining1[1])
                                    placed5ssecond = min((second3-6*placed6ssecond)//5,remaining1[0])
                                    remaining2 = [remaining1[0]-placed5ssecond,remaining1[1]-placed6ssecond]

                                    if sum(remaining2)==0:
                                        new3.extend([new31,new32])
                                        new3actual.extend([first3actual,second3actual])
                                        new3init.extend([[placed5sfirst,placed6sfirst],[placed5ssecond,placed6ssecond]])
                                        used3.add(n);used5.add(m)
                                        size5[m]=[]; init5[m]=[];size3[n]=[];init3[n]=[];actual3[n]=[];actual5[m]=[]
                                        size2.append(new2); init2.append([placed5s2s,placed6s2s]); actual2.append(the2actual)
                                        placedFlag, progressFlag = True, True

        size3.extend(new3); init3.extend(new3init); actual3.extend(new3actual)
        packed3 = [(s,i,a) for s,i,a in zip(size3, init3, actual3) if s]
        packed5 = [(s,i,a) for s,i,a in zip(size5, init5, actual5) if s]
        size3, init3, actual3 = (map(list, zip(*packed3)) if packed3 else ([], [], []))
        size5, init5, actual5 = (map(list, zip(*packed5)) if packed5 else ([], [], []))
    new4, new4init, new4actual = [],[],[]
    used4.clear()
    if len(size4)>=2:
        for m in range(0,len(size4)-1):
            if m in used4:
                continue
            for n in range(m+1,len(size4)):
                if n in used4 or m in used4:
                    continue
                total5s, total6s = init4[m][0]+init4[n][0],init4[m][1]+init4[n][1]
                placedFlag = False
                for a in range(0,len(size4[m])-1):
                    if placedFlag:
                        break
                    for b in range(a+1,len(size4[m])):
                        if placedFlag:
                            break
                        for c in range(0,len(size4[n])-1):
                            if placedFlag:
                                break
                            for d in range(c+1,len(size4[n])):
                                if placedFlag:
                                    break
                                placed6s = min((actual4[m][a]+actual4[m][b]+actual4[n][c]+actual4[n][d])//6,total6s)
                                placed5s = min((actual4[m][a]+actual4[m][b]+actual4[n][c]+actual4[n][d]-6*placed6s)//5,total5s)
                                remaining = [total5s-placed5s,total6s-placed6s]
                                spacesL, indL = actual4[m].copy(), size4[m].copy()
                                spacesL.pop(b); indL.pop(b); spacesL.pop(a); indL.pop(a)
                                spacesR, indR = actual4[n].copy(), size4[n].copy()
                                spacesR.pop(d); indR.pop(d); spacesR.pop(c); indR.pop(c)
                                spaces, ind = spacesL+spacesR, indL+indR
                                comb, init, new2 = combine(spaces,remaining,ind)
                                if comb and m not in used4 and n not in used4:
                                    new4.append([size4[m][a],size4[m][b],size4[n][c],size4[n][d]])
                                    new4actual.append([actual4[m][a],actual4[m][b],actual4[n][c],actual4[n][d]])
                                    used4.add(n);used4.add(m)
                                    new4init.append([placed5s,placed6s])
                                    size4[n]=[]; init4[n]=[];size4[m]=[];init4[m]=[];actual4[n]=[];actual4[m]=[]
                                    size2.extend(comb); init2.extend(init); actual2.extend(new2)
                                    placedFlag, progressFlag = True, True
        size4.extend(new4); init4.extend(new4init); actual4.extend(new4actual)
        packed4 = [(s,i,a) for s,i,a in zip(size4, init4, actual4) if s]
        size4, init4, actual4 = (map(list, zip(*packed4)) if packed4 else ([], [], []))
    used3.clear()
    if len(size3)>=2:
        for m in range(0,len(size3)-1):
            if m in used3:
                continue
            for n in range(m+1,len(size3)):
                if n in used3 or m in used3:
                    continue
                total5s, total6s = init3[m][0]+init3[n][0],init3[m][1]+init3[n][1]
                spaces = actual3[m].copy()+actual3[n].copy()
                ind = size3[m].copy()+size3[n].copy()
                comb, init, new2 = combine(spaces,[total5s,total6s],ind)
                if comb and m not in used3 and n not in used3:
                    used3.add(n);used3.add(m)
                    size3[n]=[]; init3[n]=[];size3[m]=[];init3[m]=[];actual3[n]=[];actual3[m]=[]
                    size2.extend(comb); init2.extend(init); actual2.extend(new2)
                    placedFlag, progressFlag = False,True
        packed3 = [(s,i,a) for s,i,a in zip(size3, init3, actual3) if s]
        size3, init3, actual3 = (map(list, zip(*packed3)) if packed3 else ([], [], []))
    used4.clear()
    if len(size4)>=2:
        for m in range(0,len(size4)-1):
            if m in used4:
                continue
            for n in range(m+1,len(size4)):
                if n in used4 or m in used4:
                    continue
                total5s, total6s = init4[m][0]+init4[n][0],init4[m][1]+init4[n][1]
                spaces = actual4[m].copy()+actual4[n].copy()
                ind = size4[m].copy()+size4[n].copy()
                comb, init, new2 = combine(spaces,[total5s,total6s],ind)
                if comb and m not in used4 and n not in used4:
                    used4.add(n);used4.add(m)
                    size4[n]=[]; init4[n]=[];size4[m]=[];init4[m]=[]
                    actual4[n]=[];actual4[m]=[]
                    size2.extend(comb); init2.extend(init); actual2.extend(new2)
                    placedFlag, progressFlag = False,True
        packed4 = [(s,i,a) for s,i,a in zip(size4, init4, actual4) if s]
        size4, init4, actual4 = (map(list, zip(*packed4)) if packed4 else ([], [], []))

    used3.clear()
    new3, new3init, new3actual = [], [], []
    if len(size3)>=3:
        for m in range(0,len(size3)-2):
            if m in used3:
                continue
            for n in range(m+1,len(size3)-1):
                if n in used3 or m in used3:
                    continue
                for o in range(n+1,len(size3)):
                    if n in used3 or m in used3 or o in used3:
                        continue
                    total5s, total6s = init3[m][0]+init3[n][0]+init3[o][0],init3[m][1]+init3[n][1]+init3[o][1]
                    placedFlag = False
                    for a in range(len(size3[m])):
                        if placedFlag:
                            break
                        for b in range(len(size3[n])):
                            if placedFlag:
                                break
                            for c in range(len(size3[o])):
                                if placedFlag:
                                    break
                                placed6s = min((actual3[m][a]+actual3[n][b]+actual3[o][c])//6,total6s)
                                placed5s = min((actual3[m][a]+actual3[n][b]+actual3[o][c]-6*placed6s)//5,total5s)
                                remaining = [total5s-placed5s,total6s-placed6s]
                                spacesL, indL = actual3[m].copy(), size3[m].copy()
                                spacesL.pop(a); indL.pop(a)
                                spacesM, indM = actual3[n].copy(), size3[n].copy()
                                spacesM.pop(b); indM.pop(b)
                                spacesR, indR = actual3[o].copy(), size3[o].copy()
                                spacesR.pop(c); indR.pop(c)
                                spaces, ind = spacesL+spacesM+spacesR, indL+indM+indR
                                comb, init, new2 = combine(spaces,remaining,ind)
                                if comb and m not in used3 and n not in used3 and o not in used3:
                                    new3.append([size3[m][a],size3[n][b],size3[o][c]])
                                    new3actual.append([actual3[m][a],actual3[n][b],actual3[o][c]])
                                    used3.add(n);used3.add(m);used3.add(o)
                                    new3init.append([placed5s,placed6s])
                                    size3[n]=[]; init3[n]=[];size3[m]=[];init3[m]=[]; size3[o]=[];init3[o]=[]
                                    actual3[n]=[];actual3[m]=[];actual3[o]=[]
                                    size2.extend(comb); init2.extend(init); actual2.extend(new2)
                                    placedFlag, progressFlag = True,True
        size3.extend(new3); init3.extend(new3init); actual3.extend(new3actual)
        packed3 = [(s,i,a) for s,i,a in zip(size3, init3, actual3) if s]
        size3, init3, actual3 = (map(list, zip(*packed3)) if packed3 else ([], [], []))

    used4.clear()
    if len(size4)>=2:
        for m in range(0,len(size4)-1):
            if m in used4:
                continue
            for n in range(m+1,len(size4)):
                if n in used4 or m in used4:
                    continue
                total5s, total6s = init4[m][0]+init4[n][0],init4[m][1]+init4[n][1]
                placedFlag = False
                for a in range(0,len(size4[m])):
                    if placedFlag:
                        break
                    for b in range(0,len(size4[m])):
                        if placedFlag:
                            break
                        if b==a:
                            continue
                        for c in range(0,len(size4[n])):
                            if placedFlag:
                                break
                            for d in range(0,len(size4[n])):
                                if placedFlag:
                                    break
                                if d==c:
                                    continue
                                the2 = actual4[m][a]+actual4[n][c]
                                first3 = actual4[m][b] + sum(actual4[n][:min(c,d)]) + sum(actual4[n][min(c,d)+1:max(c,d)]) + sum(actual4[n][max(c,d)+1:])
                                second3 = actual4[n][d] + sum(actual4[m][:min(a,b)]) + sum(actual4[m][min(a,b)+1:max(a,b)]) + sum(actual4[m][max(a,b)+1:])

                                the2actual = [actual4[m][a]]+[actual4[n][c]]
                                first3actual = [actual4[m][b]] + list(actual4[n][:min(c,d)]) + list(actual4[n][min(c,d)+1:max(c,d)]) + list(actual4[n][max(c,d)+1:])
                                second3actual = [actual4[n][d]] + list(actual4[m][:min(a,b)]) + list(actual4[m][min(a,b)+1:max(a,b)]) + list(actual4[m][max(a,b)+1:])

                                new2 = [size4[m][a]]+[size4[n][c]]
                                new31 = [size4[m][b]] + list(size4[n][:min(c,d)]) + list(size4[n][min(c,d)+1:max(c,d)]) + list(size4[n][max(c,d)+1:])
                                new32 = [size4[n][d]] + list(size4[m][:min(a,b)]) + list(size4[m][min(a,b)+1:max(a,b)]) + list(size4[m][max(a,b)+1:])

                                placed6s2s = min(the2//6,total6s)
                                placed5s2s = min((the2-6*placed6s2s)//5,total5s)
                                remaining = [total5s-placed5s2s,total6s-placed6s2s]

                                placed6sfirst = min(first3//6,remaining[1])
                                placed5sfirst = min((first3-6*placed6sfirst)//5,remaining[0])
                                remaining1 = [remaining[0]-placed5sfirst,remaining[1]-placed6sfirst]

                                placed6ssecond = min(second3//6,remaining1[1])
                                placed5ssecond = min((second3-6*placed6ssecond)//5,remaining1[0])
                                remaining2 = [remaining1[0]-placed5ssecond,remaining1[1]-placed6ssecond]

                                if sum(remaining2)==0:
                                    size3.extend([new31,new32])
                                    actual3.extend([first3actual,second3actual])
                                    init3.extend([[placed5sfirst,placed6sfirst],[placed5ssecond,placed6ssecond]])
                                    used4.add(n);used4.add(m)
                                    size4[n]=[]; init4[n]=[];size4[m]=[];init4[m]=[];actual4[n]=[];actual4[m]=[]
                                    size2.append(new2); init2.append([placed5s2s,placed6s2s]); actual2.append(the2actual)
                                    placedFlag, progressFlag = True, True

        packed4 = [(s,i,a) for s,i,a in zip(size4, init4, actual4) if s]
        size4, init4, actual4 = (map(list, zip(*packed4)) if packed4 else ([], [], []))

    used4.clear()
    used2 = set()
    if len(size4)>=1 and len(size2)>=1:
        for m in range(0,len(size4)):
            if m in used4:
                continue
            for n in range(0,len(size2)):
                if n in used2 or m in used4:
                    continue
                placedFlag=False
                total5s = init4[m][0]+init2[n][0]
                total6s = init4[m][1]+init2[n][1]
                for a in range(0,len(size4[m])-1):
                    if placedFlag:
                        break
                    for b in range(a+1,len(size4[m])):
                        if placedFlag:
                            break
                        new31 = [size2[n][0], size4[m][a], size4[m][b]]
                        new32 = [size2[n][1]] + list(size4[m][:a]) + list(size4[m][a+1:b]) + list(size4[m][b+1:])

                        first3actual = [actual2[n][0], actual4[m][a], actual4[m][b]]
                        second3actual = [actual2[n][1]] + list(actual4[m][:a]) + list(actual4[m][a+1:b]) + list(actual4[m][b+1:])

                        first3 = actual2[n][0] + actual4[m][a] + actual4[m][b]
                        second3 = actual2[n][1] + sum(actual4[m][:a]) + sum(actual4[m][a+1:b]) + sum(actual4[m][b+1:])

                        placed6s1 = min(first3//6,total6s)
                        placed5s1 = min((first3-6*placed6s1)//5,total5s)
                        remaining = [total5s-placed5s1,total6s-placed6s1]

                        placed6s2 = min(second3//6,remaining[1])
                        placed5s2 = min((second3-6*placed6s2)//5,remaining[0])
                        remaining1 = [remaining[0]-placed5s2,remaining[1]-placed6s2]
                        if sum(remaining1)==0:
                            size3.extend([new31,new32])
                            init3.extend([[placed5s1,placed6s1],[placed5s2,placed6s2]])
                            actual3.extend([first3actual,second3actual])
                            used4.add(m); used2.add(n)
                            size4[m]=[]; size2[n]=[]; init4[m]=[]; init2[n]=[]; actual4[m]=[]; actual2[n]=[]
                            placedFlag, progressFlag = True, True

        packed4 = [(s,i,a) for s,i,a in zip(size4, init4, actual4) if s]
        size4, init4, actual4 = (map(list, zip(*packed4)) if packed4 else ([], [], []))
        packed2 = [(s,i,a) for s,i,a in zip(size2, init2, actual2) if s]
        size2, init2, actual2 = (map(list, zip(*packed2)) if packed2 else ([], [], []))

    used5.clear()
    used2.clear()
    if len(size5)>=1 and len(size2)>=1:
        for m in range(0,len(size5)):
            if m in used5:
                continue
            for n in range(0,len(size2)):
                if n in used2 or m in used5:
                    continue
                placedFlag=False
                total5s = init5[m][0]+init2[n][0]
                total6s = init5[m][1]+init2[n][1]
                for a in range(0,len(size5[m])-1):
                    if placedFlag:
                        break
                    for b in range(a+1,len(size5[m])):
                        if placedFlag:
                            break
                        for c in range(len(size2[n])):
                            if placedFlag:
                                break
                            new3 = [size2[n][c], size5[m][a], size5[m][b]]
                            new4 = list(size2[n][:c])+ list(size2[n][c+1:]) + list(size5[m][:a]) + list(size5[m][a+1:b]) + list(size5[m][b+1:])

                            first3actual = [actual2[n][c], actual5[m][a], actual5[m][b]]
                            first4actual = list(actual2[n][:c])+ list(actual2[n][c+1:]) + list(actual5[m][:a]) + list(actual5[m][a+1:b]) + list(actual5[m][b+1:])

                            first3 = actual2[n][c] + actual5[m][a] + actual5[m][b]
                            first4 = sum(actual2[n][:c])+ sum(actual2[n][c+1:]) + sum(actual5[m][:a]) + sum(actual5[m][a+1:b]) + sum(actual5[m][b+1:])

                            placed6s1 = min(first4//6,total6s)
                            placed5s1 = min((first4-6*placed6s1)//5,total5s)
                            remaining = [total5s-placed5s1,total6s-placed6s1]

                            placed6s2 = min(first3//6,remaining[1])
                            placed5s2 = min((first3-6*placed6s2)//5,remaining[0])
                            remaining1 = [remaining[0]-placed5s2,remaining[1]-placed6s2]
                            if sum(remaining1)==0:
                                size3.append(new3); size4.append(new4)
                                init3.append([placed5s2,placed6s2]); init4.append([placed5s1,placed6s1])
                                actual3.append(first3actual); actual4.append(first4actual)
                                used5.add(m); used2.add(n)
                                size5[m]=[]; size2[n]=[]; init5[m]=[]; init2[n]=[]; actual5[m]=[]; actual2[n]=[]
                                placedFlag, progressFlag = True, True

        packed5 = [(s,i,a) for s,i,a in zip(size5, init5, actual5) if s]
        size5, init5, actual5 = (map(list, zip(*packed5)) if packed5 else ([], [], []))
        packed2 = [(s,i,a) for s,i,a in zip(size2, init2, actual2) if s]
        size2, init2, actual2 = (map(list, zip(*packed2)) if packed2 else ([], [], []))

    size5 = [[x+1 for x in combo]for combo in size5]
    size4 = [[x+1 for x in combo]for combo in size4]
    size3 = [[x+1 for x in combo]for combo in size3]
    size2 = [[x+1 for x in combo]for combo in size2]
    other = [[x+1 for x in combo]for combo in other]

    '''
    In theory, 5+3+3 is also possible, for example 5,4,3  2,2,2  5,5,5,3 or 4,4,4  3,2,1  3,1,1,1. I have yet 
    to see it in practice or stress testing. It can be broken into 2,2,3,3.
    '''

    return size5+size4+size3+size2+other, init5+init4+init3+init2+init_other, progressFlag