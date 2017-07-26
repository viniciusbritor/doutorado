#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pyspark import SparkContext,SparkConf
from pyspark.streaming.flume import FlumeUtils
from pyspark.streaming import StreamingContext
import pyspark.storagelevel as strlv
from pyspark.serializers import PairDeserializer, NoOpSerializer, UTF8Deserializer, read_int
from scipy import stats
import numpy as np
from operator import add
import pandas as pd
import networkx as nx
import itertools as it

import collections 
#from matplotlib import pyplot as plt
import subprocess
from itertools import izip


#conf = SparkConf().setAppName('estudo').setMaster("local[4]").set("spark.driver.allowMultipleContexts", "true").set("spark.storage.memoryFraction", "0.5")

conf = SparkConf().setAppName('estudo').setMaster("local[4]")

sc = SparkContext(conf=conf)

ssc=StreamingContext(sc,5)



flumeStream = FlumeUtils.createStream(ssc, "localhost", 9990)



def spl(x):
	return x.split(' ')

def map1(x):
	return (x,1)


def conta(x):
	collections.Counter(x)

def unlist(x):
	return sum(x,[])

def totext(x):
	return " ".join(str(i) for i in x)

#funções da qualificação ##
#função limpeza de delimitadores ##

def clean_all(x):
    return x.lower().replace('\n','').replace(';','').replace('\t','').replace('\r','').upper()

# função Tag alvo
def interest(x):
    if u'RECORD_NUMBER' in x or  u'SESSION_ID' in x  or  u'GRAMMAR_LABEL' in x or u'RESULT[0]' in x or  u'STATE_DURATION' in x or u'PROMPT_DELAY' in x or  u'PROMPT_DURATION' in x or u'CALL_REMOTE_URL' in x :
        return x
# funções de limpeza e conversão
def grammar_limpa(x):
    x1=x[x.find('#'):]
    return str(x1[1:x1.find('<')])

def session_id_limpa(x):
    x1=x[x.find('=')+1:].strip()
    return x1

def prompt_delay_limpa(x):
    return x[x.find('=')+1:].strip()

def prompt_duration_limpa(x):
    x1=x[x.find('=')+1:].strip()
    return x1 #str(x1[1:x1.find('(')])


# ifelse
def ifelse(x):
    if  u'SESSION_ID' in x:
        return 'SESSION_ID='+ session_id_limpa(x)
    if  'RESULT[0]' in x:
        return 'RESULT='+prompt_delay_limpa(x)
    if u'GRAMMAR_LABEL' in x:
        return 'GRAMMAR_LABEL='+grammar_limpa(x)
    if  u'RECORD_NUMBER' in x:
        return 'RECORD_NUMBER='+prompt_delay_limpa(x)
    if  u'PROMPT_DELAY' in x:
        return 'PROMPT_DELAY='+prompt_delay_limpa(x)
    if  u'PROMPT_DURATION' in x:
        return 'PROMPT_DURATION='+prompt_duration_limpa(x)
    if  u'STATE_DURATION' in x:
        return 'STATE_DURATION='+prompt_delay_limpa(x)
    if  u'CALL_REMOTE_URL' in x:
        return 'CALL_REMOTE_URL='+prompt_delay_limpa(x)
     
    else:    
        return x

    
    
 



def positionid(x):
	guarda=[]
	rodada=0
	for i  in range(len(x)):
		if 'SESSION_ID' in x[i]:
			rodada=rodada+1			
			passo=[]
			passo.append(rodada)			
			passo.append(x[i])
			k=i+1
			 
			try:
				while  'SESSION_ID' not in x[k]:	
					passo.append(x[k])
					k=k+1
				guarda.append(passo)
					
			except:
				pass
			
				
	return guarda
	return session_cont





def validaposicao(x):
        reposicao=['SESSION_ID','RECORD_NUMBER','GRAMMAR_LABEL','PROMPT_DELAY','PROMPT_DURATION','RESULT','STATE_DURATION','CALL_REMOTE_URL' ]
        store=[]
	index=[]
        contador_passo=0
	linha=x[0]
	store.append(linha)
	for i in reposicao: # copiar codigo da qualificação para tentar pegar hang up e ultimo passo
		try:		
			store.append(x[[i in str(s) for s in x].index(True)])
		except ValueError:
			if i=='RECORD_NUMBER':
                    		store.append(str(i)+'NULL'+str(contador_passo))
	                if i in ['GRAMMAR_LABEL','RESULT']:
                 		if (True in ['HANG_UP' in str(s) for s in x ]):
					store.append(str(i)+'='+str('HANG_UP'))                                 
                  		else:
		                        store.append(str(i)+'='+str('NULL'))
                        
               		else:
				store.append(str(i)+'=0')
        	contador_passo+=1

		#	if 'PROMPT_DURATION' in i:
		#		store.append(u'PROMPT_DURATION=None')
		#	if u'RESULT' in i:
		#		store.append(u'RESULT=None')
		#	if u'STATE_DURATION' in i:
		#		store.append(u'STATE_DURATION=None')
		#	if u'CALL_REMOTE_URL' in i:
		#		store.append(i)
			 
#		if i in ['GRAMMAR_LABEL','RESULT']:
                 #   if (True in ['HANG_UP' in s for s in atual_x ]):
                  #      correct_tmp.append(str(repos)+'='+str('HANG_UP'))                                 
                  #  else:
                   #     correct_tmp.append(str(repos)+'='+str('NULL'))
                        
               # else:
                #    correct_tmp.append(str(repos)+'=0')
	return 	store
		


def contasession(x):
	 session_cont=[k  for k in range(len(x)) if 'SESSION_ID' in str(x[k])]	
	 saida=[]    
	 for i in range(len(session_cont)):
		if i==max(range(len(session_cont))):
			atual=[i+1]+x[session_cont[i]:]

			saida.append(atual)
		else:
		        atual=[i+1]+x[session_cont[i]:session_cont[i+1]]

		        saida.append(atual)
	 return saida

# separa em duas colunas			
def split2(x):
    store=[]
    for i in range(len(x)):
        if i==0:
            store.append(['passo',x[0]])
        else: 
            store.append(str(x[i]).split("="))
    return np.array(store)


def asarray(x):
    return x[:,1]


def limpaprompt2(x):
    tmp=np.delete(x, 5)
    tmp2=np.insert(tmp,5,x[5][0:x[5].find("(")-1])
    return tmp2



log = flumeStream.map(lambda x: x[1])
log_p1 = log.map(lambda x : map(clean_all,x.split('\r\n')))
log_p2 = log_p1.filter(lambda x: filter(interest,x)) # mudei map para filter, antes não funcionava. Ponto de atenção
#log_p3 = log_p2.map(lambda x: map(ifelse,x)).reduce(add).map(lambda x: positionid(x)).map(lambda x: map(validaposicao,x))
#log_p3 = log_p2.map(lambda x: map(ifelse,x)).reduce(add).map(lambda x: contasession(x)).map(lambda x: map(validaposicao,x)).map(lambda x: map(split2,x)).map(lambda x:map(asarray,x[0]))#.map(lambda x:limpaprompt2(x))

tel_chamada = log_p2.map(lambda x: map(ifelse,x)).reduce(add).map(lambda x: contasession(x)).map(lambda x: map(validaposicao,x)).map(lambda x: map(split2,x)).map(lambda x:map(asarray,x)[0][8])#.map(lambda x:limpaprompt2(x))

def telefoneall(x,tel):
	if x[8]=='0':
		return tel
	else:
		return x[8]

log_p3 = log_p2.map(lambda x: map(ifelse,x)).reduce(add).map(lambda x: contasession(x)).map(lambda x: map(validaposicao,x)).map(lambda x: map(split2,x)).map(lambda x:map(asarray,x)).map(lambda x:map(limpaprompt2,x)).map(lambda x : map(telefoneall,x,tel_chamada))


#log_p3 = log_p2.map(lambda x: map(ifelse,x)).map(lambda x: unlis(map(split_equal,x))) #.reduce(add).map(lambda x: positionid(x))


log_p3.pprint()  
path="/user/vinicius/log/write"


  
#subprocess.call(["hadoop", "fs", "-rm","-R", "-f", path])
 
 

 
#subprocess.call(["hadoop", "fs", "-mkdir",path])
 
 

#log_p3.repartition(1).saveAsTextFiles("hdfs://localhost/user/vinicius/log/write/resp")
#log_p3.repartition(1).saveAsTextFiles("hdfs://localhost/user/vinicius/log/write/resp")



ssc.start()             # Start the computation
ssc.awaitTermination()  # Wait for the computation to terminate
