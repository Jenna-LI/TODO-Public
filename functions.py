import nltk
import re
from datetime import datetime, timedelta
from word2number import w2n
import dateutil
from dateutil.relativedelta import *
from dateutil.parser import parse


grammar = '''
    PLACE:{<IN><DT>?(<FACILITY>|<PERSON>|<ORGANIZATION>((<IN><GPE>)|(<JJ><NN>))?)<POS>?<NN>?}
    TIME:{<IN><CD><NNS><CC><CD><NNS>}
    DATE:{<IN><CD><NNS>(<CC><CD><NN*>)?}
    
    TIME:{<IN><CD>+(<NN>|<JJ>|<VBP>)?<CD>?(<IN><NN>)?}    
    DATE:{(<DT>?<CD><NN>?|<JJ>)<IN>?<NNP>}
    DATE:{(<IN>|<DT>)<NNP><CD>?<CD>?}
    DATE:{<NN><IN><TIME>?$}
    DATE:{<NNP>(<CD><NN>?|<JJ>)}
    DATE:{<IN><DT>(<JJ>|<CD>)(<IN>(<GPE>|<NNP>))?}
    DATE:{<JJ>(<NN>|<NNP>)}
    DATE:{<IN><DT>?<DATE>}
    DATE:{<IN><NN>$}
    PERSON:{<NNP><NNP>+}
'''



nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')



def tokenize(body):
    sentence = nltk.sent_tokenize(body)
    # ##print(sentence)
    tagged = []
    for i in sentence:
        tokens = nltk.word_tokenize(i)
        tagged.append(nltk.pos_tag(tokens))
    
    

    return tagged


def remove(body):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

    body = body.replace('\n', " ")
    body = body.replace('-', "")
    body = re.sub(regex, '', body)
    return body

def entities(tagged):
    entities = nltk.chunk.ne_chunk(tagged)
   
    cp = nltk.RegexpParser(grammar)
    result = cp.parse(entities)

    return result




def extractTree(tree, label):
    entityNames = []
    if hasattr(tree, 'label')and tree.label:
      
        if tree.label() == label:
            entityNames.append(tree)

        else:
            for child in tree:
                entityNames.extend(extractTree(child, label))
        
    return entityNames

def extractTag(tree, tag):
    tags = []
    if hasattr(tree, 'label') and tree.label:
        for child in tree:
             tags.extend(extractTag(child, tag))
    else:
        if tree[1] == tag:
            tags.append(tree[0])
    
    return tags


def extractUnits(tree):
    units = []
    nouns = extractTag(tree, "NN")
    
    nouns.extend(extractTag(tree, "NNS"))
 
    for i, noun in enumerate(nouns):
        if noun == "min":
            nouns[i] = "minutes"
        elif noun == "minute":
            nouns[i] = "minutes"
        elif noun == "hour":
            nouns[i] = "hours"
        
    for noun in nouns:
        if noun == "minutes" or noun == "hours":
            units.append(noun)

    num = extractTag(tree, "CD")
    
    num = [int(n) for n in num if n.isdigit()]
  
    return dict(zip(units, num))

def base_time(hours=0, mins=0):
 
    now = datetime.now()
    now = now.replace(hour=hours, minute=mins, second=0, microsecond=0)
    
    return now

def to_twentyfour_hours(time, meridiem):
    pHours= 0
    pMinutes = 0
    if len(time) == 2:
        pHours, pMinutes = time
    else:
        pHours = time[0]
    if pHours > 12:
        # -1 = am
        if meridiem == -1:
            raise Exception("the time is AM even though hours is greater than 12")

      
        return base_time(pHours, pMinutes)

    if meridiem == -1:
        if pHours == 12:
            pHours =0
        return base_time(pHours, pMinutes)
   

    if pHours != 12:
        if meridiem == 1:
            pHours += 12
            return base_time(pHours, pMinutes)

        # if datetime.now() < base_time(pHours+12, pMinutes):
        else:
            return base_time(pHours, pMinutes)  

        #return base_time(pHours+12, pMinutes)  
  
        
    else: 
        return base_time(pHours, pMinutes)




def parse_relative_time(units):
    now = datetime.now().replace(second=0, microsecond=0)
    if len (units) == 3:
        return now + timedelta(hours=units ['hour'], minutes= units['minute'], days=units['day'])
    if len(units)==2:
        if 'hour' in units and units['hour'] and 'minute' in units and units['minute']:
            return now + timedelta(hours=units ['hour'], minutes= units['minute'])
        elif  'day' in units and units['day'] and 'minute' in units and units['minute']:
            return now + timedelta(days=units ['day'], minutes= units['minute'])
        elif 'day' in units and units['day'] and 'hour' in units and units['hour']:
            return now + timedelta(days=units ['day'], hours= units['hour'])

    elif 'hour' in units and units['hour']:

        return now + timedelta(hours=units['hour'])

    elif 'minute' in units and units['minute']:
        return now + timedelta(minutes=units['minute'])
    

    elif 'day' in units and units['day']:
        return now + timedelta(days=units['day'])

        
def extract_meridiem(tree):
    nouns = extractTag(tree, "NN")
    pm = False
    am = False
    am_nouns = ['am', 'morning', 'AM']
    pm_nouns = ['pm', 'afternoon', 'evening', 'PM']
    found = False

    digit = extractTag(tree, 'CD')

    for i in digit:
        for a in am_nouns:
            if i.find(a) !=-1:
                nouns.append(a)
                found = True
                break
        else:
            for b in pm_nouns:
                if i.find(b) !=-1:
                    nouns.append(b)
                    found = True
                    break
            
        if found:
            break   
        
    temp = []
    temp2 = []
    for noun in am_nouns:
        if noun in nouns:
            temp.append(True)
    if any(temp):
        am = True

    for noun in pm_nouns:
        if noun in nouns:
            temp2.append(True)

    if any(temp2):
        pm = True

    if am and pm:
        raise Exception("am and pm")
    if am:
        return -1
    if pm:
        return 1
    else:
        return 0

def parse_absolute_time(tree, nums, meridiem):
    return case_24_hour(meridiem, nums)

def case_24_hour(meridiem, proposed_time):
    time = to_twentyfour_hours(proposed_time, meridiem)
    if datetime.now() > time:
        return time + timedelta(days = 1)
    else:
        return time


def parse_time(tree):
    nums = extractTag(tree, 'CD')
  
    absolute_nums = []
    relative_nums = []
    colon_split = []
    temp_num = []
    
   

    if len(nums) == 1:
        nums[0] = nums[0].replace('am', '').replace('pm', '').replace('AM','').replace('PM','')
        temp = nums[0].split(':')
        
        for num in temp:
            if num.isdigit():
                colon_split.append(int(num))
            else:
                colon_split.append(w2n.word_to_num(num))
     
        if len(colon_split) ==1 or len(colon_split) > 2:
            colon_split = None
        
    else:
        colon_split = None
        
    if not colon_split:
        amPm = False
        for num in nums:
            
            if 'am' in num or 'pm' in num or 'PM' in num or 'AM' in num:
                amPm = True
                
            num = num.replace('am', '').replace('pm', '').replace('AM','').replace('PM','')
          
            try:
                if num.isdigit():
                    temp_num.append(int(num))

                else:  
                    temp_num.append(w2n.word_to_num(num))

                if amPm:
                    break
                    
            except:
                pass

    meridiem = extract_meridiem(tree)
    units = extractUnits(tree)


    if colon_split:
        absolute_nums = colon_split
    
    # units is empty
    elif not units:
        absolute_nums = temp_num
    
    if units:
        relative_nums = units

    if absolute_nums:
        parsed_time = parse_absolute_time(tree, absolute_nums, meridiem)

    elif relative_nums:
        parsed_time = parse_relative_time(relative_nums)


    else:
        
        raise Exception( 'could not be parsed')

    return parsed_time

def extractDate(tree):
    # date = extractTag(tree,'JJ')
    # if date:
    #     if len(date)> 1:
    #         raise Exception('More than one date')
    #     else:
    #         return [int(date[0].replace('th', '').replace('st', '').replace('nd', '').replace('rd', ''))]

    # tree = extractTree(tree, 'DATE')
    # ##print('tree', tree)
    nums = extractTag(tree, "CD")
    nums.extend(extractTag(tree, 'NNS'))
    temp_num = []

    for i,num in enumerate(nums):
        
        nums[i]= num.replace('th', '').replace('st', '').replace('nd', '').replace('rd', '')

    for i,n in enumerate(nums):

        try:
            if n.isdigit():
            
                temp_num.append(int(n))
            else:
                temp_num.append(w2n.word_to_num(n))
        
        except:
            pass

    if temp_num:
        return [temp_num]
    else:
        return None

def extract_month(tree):

    months = {'January':1, 'Jan': 1, 'February': 2, 'Feb': 2, 'March':3, 'Mar': 3, "April": 4, 'Apr':4, "May": 5, 'June':6, 'Jun':6, 'July': 7, 'Jul':7, 'August':8, 'Aug': 8, 'September': 9, 'Sep': 9, 'October':10, 'Oct': 10, 'November': 11, 'Nov': 11, 'December':12, 'Dec': 12}
    found_months = []
    nouns = extractTag(tree, 'NNP')
    found_months = []
    for noun in nouns:
        if noun in months:
            found_months.append(months[noun])
       
        return found_months

def extract_weekday(tree):
    nouns = extractTag(tree, 'NNP')     

    found_days = []
    for noun in nouns:
        weekdays = week_day_to_int(noun)
        if weekdays != None:
            found_days.append(week_day_to_int(noun))
 
    return found_days

def week_day_to_int(weekday):
    weekdays = {'Monday': 0,'Mon':0, 
                'Tuesday': 1, 'Tue': 1, 
                'Wednesday': 2, 'Wed': 2, 
                'Thursday': 3, 'Thu': 3, 
                'Friday':4, 'Fri': 4, 
                'Saturday': 5, 'Sat': 5, 
                'Sunday': 6, 'Sun': 6}
    
    if weekday in weekdays:
        
        return weekdays[weekday]
    else:
        return None
    
def extract_relative_units(tree):
    adj = extractTag(tree, 'JJ')
    noun = extractTag(tree, 'NN')
    noun.extend(extractTag(tree,'NNP'))
    
   
    if 'next' in adj:
        return noun
    return None

def relative_date(tree):

    now = datetime.now()
    
    rel_units = extract_relative_units(tree)
   
    if rel_units:
        for unit in rel_units:

            if unit in ['week']:
                now = now + timedelta(days = 7)

            elif unit in ['month']:
                now = now + relativedelta(months=1)

            elif unit in ['Monday','Mon',  'Tuesday', 'Tue', 'Wednesday', 'Wed', 'Thursday', 'Thu', 'Friday', 'Fri', 'Saturday', 'Sat', 'Sunday', 'Sun']:
                
                now =  next_weekday(week_day_to_int(unit))

        return now

    units = extract_date_units(tree)
    if 'tomorrow' in units:
        now = now+ timedelta(days=1)
        return now
    else:
        return None


def extract_date_units(tree):
    nouns = extractTag(tree, 'NNS')
    nouns.extend(extractTag(tree, 'NN'))

    return nouns


def next_weekday(weekday):
    date = datetime.now()
    days_ahead = weekday - date.weekday()
    if days_ahead <= 0:
        days_ahead +=7
    
    return date + timedelta(days = days_ahead)

def next_month_date(month, date_num):
    date = datetime.now()

    month_ahead = month - date.month
    if month_ahead< 0:
        month_ahead +=12
    if month_ahead == 0 and date.day > date_num:
        month_ahead +=12
    date = date+relativedelta(months = month_ahead)
    return date.replace(day = date_num)

def next_date(date_num):
    date = datetime.now()
    if date.day > date_num:
        date = date + relativedelta(months = 1)
    return date.replace(day = date_num)



def parse_date(tree):
    relative = relative_date(tree)
    
    if relative:
        return relative
    else:
        month = extract_month(tree)
        weekday = extract_weekday(tree)
        date = extractDate(tree)
      
        if not month and date:
            return next_date(date[0][0])

        elif not month and not date and weekday:
            return next_weekday(weekday[0])

        elif month and date:
            return next_month_date(month[0], date[0][0])
        raise Exception('no date')
        

def join_date_time(date,time):

    datedate = date.date()
    timedate = time.date()
    timetime = time.time()
    dateDifference = timedate.day - datetime.now().day
    if dateDifference != 0 and datetime.now().date() == datedate:
        datedate = datedate + timedelta(dateDifference)

    return datetime.combine(datedate, timetime)

def parse_date_time(tree,sentense):
    isDate,date = parse_date_no_tree(sentense)
    if not isDate:   
        date = extractTree(tree, 'DATE')

    time = extractTree(tree, 'TIME')

    if not date and not time:
        raise Exception('no date or time')
    try:
        if date:
            if isinstance(date, list):
                date = parse_date(date[0]).replace(hour=23,minute=59, second=00)

            if time:
                try:
                    time = parse_time(time[0])
                    
                except:
                    if len(time)==2:
                        time = parse_time(time[1])
                    else:
                        date = str(date)
                        return date[:19]


                return join_date_time(date, time)

            else:
                date = str(date)
                return date[:19]

        time = parse_time(time[0])
        return join_date_time(datetime.now(), time)

    except:
        raise Exception('date or time did not work')
    


def parse_action(tree):
    node = []
    node1 = []
    node3 = []

    for i in tree:
        node.extend(extract_nodes(i, 'DATE'))
    for i in node:
        node1.extend(extract_nodes(i, 'TIME'))
    node = []
    for i in node1:
        node.extend(extract_nodes(i, 'PLACE'))
    for i in node:
        if isinstance(i, tuple):
            node3.append(i[0])
        else: 
            node3.append(i[0][0])
    return ' '.join(node3)

def extract_nodes(tree, label):
    entityNames = []
    if hasattr(tree, 'label')and tree.label:
       

        if tree.label() != label:
            entityNames.append(tree)

        else:
            for child in tree:
                entityNames.extend(extractTree(child, label))
    else:
        entityNames.append(tree)
    return entityNames

def parse_todo_list(sentences):
    todo = []



    sentence = remove(sentences)
    tag = tokenize(sentence)
    
    for a in tag:
        tree = entities(a)
        # #(tree)
        try:
            parsed_date_time = str(parse(sentence, fuzzy=True).strftime('%m- %d-%Y %H:%M'))
            parsed_actions = parse_action(tree)
            ###print(parsed_date_time, parsed_actions)
            todo.append((parsed_date_time, parsed_actions))
        except:
            pass
    return todo
            

def parse_date_no_tree(sentence):
    ###print('parse')
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:

        date = parse(sentence, fuzzy=True).strftime('%m- %d-%Y %H:%M')
        return True , date

    except ValueError:
        ###print('exception')
        return False,None



# ##print(parse_todo_list('someones birtday party is on 5/27/21 at 4:00 am'))
