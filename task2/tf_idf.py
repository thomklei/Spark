#./usr/localspark-2.1.0-bin-hadoop2.7/python/
import sys
sys.path.append("/usr/local/spark/python/")
from pyspark import SparkConf, SparkContext
from pyspark.sql import SQLContext, SparkSession
from pyspark.sql import *
from pyspark.sql.types import *
import numpy as np
from pyspark.sql import functions as funcs
from pyspark.sql import functions as col
from pyspark.sql.functions import *
from multiprocessing import Pool
import json
import numpy as np
from pyspark.ml.feature import HashingTF, IDF


def main():
    air = airbnb()
    air.joinListingsWithNeighborhood()

class airbnb():

    def __init__(self):
        self.sc = SparkContext()
        self.sqlCtx = SQLContext(self.sc)
        self.spark = SparkSession.builder.getOrCreate()
        self.hashingTF = HashingTF()
        self.listings = self.getListings()
        self.df = self.joinListingsWithNeighborhood()
        self.computeImportanceForNeighborhood('Chinatown')


    #Create listings dataset
    def getListings(self):
        df = self.spark.read.format("com.databricks.spark.csv").option("header", "true").option("delimiter", "\t") \
        .load("listings_us.csv")
        return df

    #Join neighborhoods with listings
    def joinListingsWithNeighborhood(self):
        neighborhood_df = self.spark.read.format("com.databricks.spark.csv").option("header", "true").option("mode", "DROPMALFORMED") \
        .load("San_Francisco_neighborhood.csv")
        neighborhood_df = neighborhood_df.withColumn('id', ltrim(neighborhood_df.id))
        df = self.listings.join(neighborhood_df, self.listings.id == neighborhood_df.id)
        return df

    #Compute tf-idf for a neighborhood
    def computeImportanceForNeighborhood(self, neighborhood):
        self.df.createOrReplaceTempView('df')
        res = self.spark.sql("SELECT neighborhood, description FROM df")
        res = res.rdd.groupByKey().map(lambda x: (x[0], list(x[1])))

        #Get number of times word w appears in document
        times_word_used_in_document = self.getTimesWordsUsedInDocument(res, neighborhood)

        #Get total number of words in document
        total_num_words = self.getTotalNumberOfWordsInDoc(res, neighborhood)

        #Get words into key, value pairs
        tdfDict = {}
        for word in times_word_used_in_document.collect():
            tdfDict['%s'%word[0]] = float(word[1])/total_num_words

        #Compute weights for all words in document
        self.computeWeight(tdfDict, self.computeIDF(res))

    #Compute weights for each word and return top 100 most important words
    def computeWeight(self, tdfDict, idfDict):
        import operator
        for word in tdfDict:
            tdfDict['%s'%word] = float(tdfDict.get('%s'%word,0))*float(idfDict.get('%s'%word,0))
        new = dict(sorted(tdfDict.iteritems(), key=operator.itemgetter(1), reverse=True)[:100])
        print new
        return tdfDict

    #Compute the inverse document frequency
    def computeIDF(self, res):
        import math
        idfDict = {}
        lines = self.parseRDD(res).map(lambda p: (p.split(' '))).collect()
        keys = self.parseRDD(res).flatMap(lambda p: (p.split(' '))).collect()
        for word in keys:
            idfDict['%s'%word] = 0

        #Number of documents
        tot_num_documents = len(lines)

        #Count number of documents that contain word w
        used = []
        for line in lines:
            for word in line:
                if word not in used:
                    idfDict['%s'%word] = idfDict.get('%s'%word, 0) +1
                    used.append(word)
            used = []

        #Get words into key, value pairs
        for word in idfDict:
            idfDict['%s'%word] = (float(tot_num_documents)/(float(idfDict.get('%s'%word,0))))

        return idfDict

    #Parse rdd
    def parseRDD(self, rdd):
        return rdd.map(lambda x: (x[1][0].lower()))\
                  .map(lambda i: i.replace(',', ''))\
                  .map(lambda o: o.replace('.',''))\
                  .map(lambda o: o.replace('(',''))\
                  .map(lambda o: o.replace(')',''))\
                  .map(lambda t: t.replace('!', ''))

    #Get number of times word w appears in document
    def getTimesWordsUsedInDocument(self, res, neighborhood):
        return res.filter(lambda s: s[0] == '%s'%neighborhood).map(lambda x: str(x[1]))\
                                        .map(lambda p: p.lower())\
                                        .map(lambda i: i.replace(',', ''))\
                                        .map(lambda o: o.replace('.',''))\
                                        .map(lambda n: n.replace('!', ''))\
                                        .map(lambda j: j.replace('(', ''))\
                                        .map(lambda h: h.replace(')', ''))\
                                        .map(lambda s: s.replace('\"', ''))\
                                        .map(lambda u: u.replace('\n', ''))\
                                        .map(lambda y: y.replace('\' \'', ''))\
                                        .flatMap(lambda words: words.split(' '))\
                                        .map(lambda word: (word, 1))\
                                        .reduceByKey(lambda a, b: a+b)
    #Get total number of words
    def getTotalNumberOfWordsInDoc(self, res, neighborhood):
        return  res.filter(lambda s: s[0] == '%s'%neighborhood).map(lambda x: str(x[1]))\
                            .map(lambda p: p.lower())\
                            .flatMap(lambda words: words.split(' '))\
                            .count()

if __name__ == "__main__":
    main()




























































"""times_word_usied_in_neighs = res.map(lambda x: str(x[1]))\
                            .map(lambda p: p.lower())\
                            .flatMap(lambda words: words.split(' '))\
                            .map(lambda i: i.replace(',', ''))\
                            .map(lambda o: o.replace('.',''))\
                            .map(lambda word: (word, 1))\
                            .reduceByKey(lambda a,b: a+b)"""





"""def getDescriptionOnNeighborhood(self):
    rows_am = self.df.select('description','neighborhood').collect()
    flat_array = []
    for row in rows_am:
        rows_description = self.parseDescription(row.description)
        if rows_description is not None:
            for description in rows_description:
                flat_array.append({'description' : str(description), 'neighborhood' : str(row.neighborhood)})

    dc_RDD = self.sc.parallelize(flat_array)
    df = self.spark.read.json(dc_RDD)

    df = df.select('neighborhood', 'description')
    df = df.rdd.groupByKey().mapValues(list).toDF(['neighborhood','description'])
    return df  """