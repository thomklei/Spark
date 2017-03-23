#./usr/localspark-2.1.0-bin-hadoop2.7/python/
import sys
sys.path.append("/usr/local/spark/python/")
from pyspark import SparkConf, SparkContext
from pyspark.sql import SQLContext, SparkSession
from pyspark.sql import *
from pyspark.sql.functions import *

def main():
    air = airbnb()
    #air.joinListingsWithNeighborhood()

class airbnb():

    def __init__(self):
        self.sc = SparkContext()
        self.sc.setLogLevel("ERROR")
        self.sqlCtx = SQLContext(self.sc)
        self.spark = SparkSession.builder.getOrCreate()
        self.listings = self.getListings()
        print("TF-IDF Assignment")
        print("Passed arguments " + str(sys.argv))
        args = str(sys.argv).split(',')
        self.df = self.joinListingsWithNeighborhood()
        if(args[1].strip().replace('\'', '') == '-l'):
            listing = args[2]
            self.df.createOrReplaceTempView('df')
            res = self.spark.sql("SELECT id, description FROM df")
            self.computeImportanceForNeighborhood(listing.strip().replace('\'', '').replace(']', ''), res)
        elif(args[1].strip().replace('\'', '') == '-n'):
            neighb = args[2]
            self.df.createOrReplaceTempView('df')
            res = self.spark.sql("SELECT neighbourhood, description FROM df")
            self.computeImportanceForNeighborhood(neighb.strip().replace('\'', '').replace(']', ''), res)
        else:
            print "Illegal path or argument"

        self.sc.stop()


    #Create listings dataset
    def getListings(self):
        df = self.spark.read.format("com.databricks.spark.csv").option("header", "true").option("delimiter", "\t") \
        .load("listings_us.csv")
        return df

    #Join neighborhoods with listings
    def joinListingsWithNeighborhood(self):
        neighborhood_df = self.spark.read.format("com.databricks.spark.csv").option("header", "true").option("delimiter", "\t")\
        .load('listings_ids_with_neighborhoods.tsv')
        neighborhood_df = neighborhood_df.withColumn('id', ltrim(neighborhood_df.id))
        df = self.listings.join(neighborhood_df,["id"])
        return df

    #Compute tf-idf for a neighborhood
    def computeImportanceForNeighborhood(self, neigh, res):
        res = res.rdd.groupByKey().map(lambda x: (x[0], list(x[1])))

        #Get number of times word w appears in document
        times_word_used_in_document = self.getTimesWordsUsedInDocument(res, neigh)

        #Get total number of words in document
        total_num_words = self.getTotalNumberOfWordsInDoc(res, neigh)

        #Get words into key, value pairs
        tdfDict = {}
        for word in times_word_used_in_document.collect():
            tdfDict['%s'%word[0]] = float(word[1])/total_num_words

        #print "Number of times word 'the' used in document: %d"%tdfDict.get('the', 0)
        print "Total number of words: ", total_num_words

        #Compute weights for all words in document
        self.computeWeight(tdfDict, self.computeIDF(res))

    #Compute weights for each word and return top 100 most important words
    def computeWeight(self, tdfDict, idfDict):
        import operator
        for word in tdfDict:
            tdfDict['%s'%word] = float(tdfDict.get('%s'%word,0))*float(idfDict.get('%s'%word,0))

        mydict = dict(sorted(tdfDict.iteritems(), key=operator.itemgetter(1), reverse=True)[:100])
        mydict = [(k, mydict[k]) for k in sorted(mydict, key=mydict.get, reverse=True)]
        with open('imp.tsv', 'w') as f:
            f.write('\n'.join('%s %s'%x for x in mydict))

    #Compute the inverse document frequency
    def computeIDF(self, res):
        import math
        idfDict = {}
        lines = self.parseRDD(res).map(lambda p: (p.split(' '))).collect()
        keys = self.parseRDD(res).flatMap(lambda p: p.split(' ')).collect()
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

        print "Number of documents that contain the word 'the': %d"%idfDict.get('the',0)
        #print "Number of documents: ", tot_num_documents

        #Get words into key, value pairs
        for word in idfDict:
            idfDict['%s'%word] = (float(tot_num_documents)/(float(idfDict.get('%s'%word,0))))

        return idfDict

    #Parse rdd
    def parseRDD(self, rdd):
        return rdd.map(lambda x: str(x[1]).lower())\
                .map(lambda x: x.replace(".", "") \
                .replace("!", "").replace("?", "").replace(",", " ") \
                .replace("/", " ").replace("\"", "").replace(" - ", " ") \
                .replace(":", " ").replace(";", " ").replace("(", "") \
                .replace(")", "").replace("*", "").replace("+", "").replace('[', '').replace(']', '') \
                .replace("|", "").replace("~", ""))


    #Get number of times word w appears in document
    def getTimesWordsUsedInDocument(self, res, neighborhood):
        return res.filter(lambda s: s[0] == '%s'%neighborhood)\
                                        .map(lambda x: str(x[1]))\
                                        .map(lambda x: x.replace(".", "") \
                                        .replace("!", "").replace("?", "").replace(",", " ") \
                                        .replace("/", " ").replace("\"", "").replace(" - ", " ") \
                                        .replace(":", " ").replace(";", " ").replace("(", "").replace('[', '').replace(']', '') \
                                        .replace(")", "").replace("*", "").replace("+", "") \
                                        .replace("|", "").replace("~", ""))\
                                        .flatMap(lambda words: words.split(' '))\
                                        .map(lambda p: p.lower())\
                                        .map(lambda word: (word, 1))\
                                        .reduceByKey(lambda a, b: a+b)
    #Get total number of words
    def getTotalNumberOfWordsInDoc(self, res, neighborhood):
        #print (res.filter(lambda s: s[0] == '%s'%neighborhood)).map(lambda x: str(x[1])).flatMap(lambda b: b.split(' ')).count()
        #b.coalesce(1).saveAsTextFile('b')
        return  res.filter(lambda s: s[0] == '%s'%neighborhood).map(lambda x: str(x[1]))\
                            .map(lambda p: p.lower())\
                            .map(lambda x: x.replace(".", "") \
                            .replace("!", "").replace("?", "").replace(",", " ") \
                            .replace("/", " ").replace("\"", "").replace(" - ", " ").replace('[', '').replace(']', '') \
                            .replace(":", " ").replace(";", " ").replace("(", "") \
                            .replace(")", "").replace("*", "").replace("+", "") \
                            .replace("|", "").replace("~", ""))\
                            .map(lambda p: p.lower())\
                            .flatMap(lambda words: words.split(' '))\
                            .distinct().count()



if __name__ == "__main__":
    main()
