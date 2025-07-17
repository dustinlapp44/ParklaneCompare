import re
import itertools
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
import math
import pandas as pd

debug_catch = False

@dataclass
class Record:
    """Represents a data record with text and numeric components"""
    description: str
    numbers: List[str]  # List of extracted numbers/codes
    raw_data: Dict  # Original record data
    
@dataclass
class Match:
    """Represents a match between two records"""
    record1: Record
    record2: Record
    similarity_score: float
    text_score: float
    number_score: float
    confidence: str  # 'high', 'medium', 'low'
    debug_catch: bool = False  # Debug flag to catch specific cases

    def to_string(self) -> str:
        """Return a string representation of the match"""
        return (f"Match between '{self.record1.description}' and '{self.record2.description}': "
                f"Score: {self.similarity_score:.3f} ({self.confidence}), "
                f"Text Score: {self.text_score:.3f}, Number Score: {self.number_score:.3f}")
    
    def to_csv(self) -> str:
        """Return a CSV representation of the match"""
        return (f"{self.record1.description},{self.record2.description},"
                f"{self.similarity_score:.3f},{self.text_score:.3f},{self.number_score:.3f},"
                f"{self.confidence}")

class FuzzyMatcher:
    def __init__(self, text_weight=0.3, number_weight=0.7, similarity_threshold=0.6):
        self.text_weight = text_weight
        self.number_weight = number_weight
        self.similarity_threshold = similarity_threshold
    
    def extract_numbers(self, text: str) -> List[str]:
        """Extract all numeric sequences from text"""
        # Find all sequences of digits, including phone numbers, addresses, etc.
        numbers = re.findall(r'\d+', text)
        return numbers
    
    def jaro_winkler_similarity(self, s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity between two strings"""
        if not s1 or not s2:
            return 0.0
        
        # Simple implementation - for production, consider using python-Levenshtein
        matcher = SequenceMatcher(None, s1.lower(), s2.lower())
        return matcher.ratio()
    
    def cosine_similarity(self, s1: str, s2: str) -> float:
        """Calculate cosine similarity between two strings using word vectors"""
        words1 = set(s1.lower().split())
        words2 = set(s2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        return len(intersection) / (math.sqrt(len(words1)) * math.sqrt(len(words2)))
    
    def text_similarity(self, text1: str, text2: str) -> float:
        """Calculate combined text similarity score"""
        jaro_score = self.jaro_winkler_similarity(text1, text2)
        cosine_score = self.cosine_similarity(text1, text2)
        
        # Combine both scores with equal weight
        return (jaro_score + cosine_score) / 2
    
    def number_similarity(self, numbers1: List[str], numbers2: List[str]) -> float:
        """Calculate similarity between two lists of numbers"""
        if self.debug_catch:
            pass
        if not numbers1 or not numbers2:
            return 0.0
        
        matches = 0
        total_comparisons = 0
        for num1 in numbers1:
            total_comparisons += 1
            if num1 in numbers2:
                matches += 1
            
        ## Check for exact matches
        #for num1 in numbers1:
        #    for num2 in numbers2:
        #        total_comparisons += 1
        #        if num1 == num2:
        #            matches += 1
        #        elif self._partial_number_match(num1, num2):
        #            matches += 0.5  # Partial credit for similar numbers
        
        return matches / total_comparisons if total_comparisons > 0 else 0.0
    
    def _partial_number_match(self, num1: str, num2: str) -> bool:
        """Check if two numbers are partially similar"""
        # Consider numbers similar if they share significant digits
        if len(num1) >= 4 and len(num2) >= 4:
            # Check if they share at least 3 consecutive digits
            for i in range(len(num1) - 2):
                substr = num1[i:i+3]
                if substr in num2:
                    return True
        return False
    
    def calculate_similarity(self, record1: Record, record2: Record) -> float:
        """Calculate overall similarity between two records"""
        if record1.description == 'Alaska Center 400 JB32522':
            self.debug_catch = True
        else:
            self.debug_catch = False
        text_score = self.text_similarity(record1.description, record2.description)
        number_score = self.number_similarity(record1.numbers, record2.numbers)
        
        # Weighted combination
        total_score = (text_score * self.text_weight) + (number_score * self.number_weight)
        return total_score, text_score, number_score
    
    def get_confidence_level(self, score: float) -> str:
        """Classify confidence level based on score"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.6:
            return 'medium'
        else:
            return 'low'
    
    def create_record(self, description: str, raw_data: Dict = None) -> Record:
        """Create a Record object with extracted numbers"""
        numbers = self.extract_numbers(description)
        return Record(
            description=description,
            numbers=numbers,
            raw_data=raw_data or {}
        )
    
    def find_matches(self, table1: List[Record], table2: List[Record]) -> List[Match]:
        """Find all potential matches between two tables"""
        matches = []
        match_found = False
        no_match1 = []
        no_match2 = []
        
        for record1 in table1:
            for record2 in table2:
                total_score, text_score, number_score = self.calculate_similarity(record1, record2)
                
                if total_score >= self.similarity_threshold:
                    confidence = self.get_confidence_level(total_score)
                    match = Match(
                        record1=record1,
                        record2=record2,
                        similarity_score=total_score,
                        text_score=text_score,
                        number_score=number_score,
                        confidence=confidence
                    )
                    matches.append(match)
                    match_found = True
                    break  # Stop after first match to avoid duplicates in output
            if not match_found:
                # If no match found for this record, add to no_match1 list
                no_match1.append(record1)
                
            match_found = False
        
        match_found = False
        for record2 in table2:
            for record1 in table1:
                total_score, text_score, number_score = self.calculate_similarity(record1, record2)
                
                if total_score >= self.similarity_threshold:
                    confidence = self.get_confidence_level(total_score)
                    match = Match(
                        record1=record1,
                        record2=record2,
                        similarity_score=total_score,
                        text_score=text_score,
                        number_score=number_score,
                        confidence=confidence
                    )
                    if match not in matches:  # Avoid duplicates
                        matches.append(match)
                    match_found = True
                    break  # Stop after first match to avoid duplicates in output
            if not match_found:
                # If no match found for this record, add to no_match2 list
                no_match2.append(record1)
                
            match_found = False
        
        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches, no_match1, no_match2
    
    def find_duplicates_within_table(self, table: List[Record]) -> List[Match]:
        """Find duplicates within a single table"""
        matches = []
        
        for i, record1 in enumerate(table):
            for j, record2 in enumerate(table[i+1:], i+1):
                total_score, text_score, number_score = self.calculate_similarity(record1, record2)
                
                if total_score >= self.similarity_threshold:
                    confidence = self.get_confidence_level(total_score)
                    match = Match(
                        record1=record1,
                        record2=record2,
                        similarity_score=total_score,
                        text_score=text_score,
                        number_score=number_score,
                        confidence=confidence
                    )
                    matches.append(match)
                    #break  # Stop after first match to avoid duplicates in output
        
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches

# Example usage
if __name__ == "__main__":
    # Initialize the matcher
    verbose = False
    alaska_pmc = pd.read_csv('Alaska Center - PMC Data.csv', skiprows=1)
    alaska_property = pd.read_csv('Alaska Center - Property Data.csv', skiprows=1)

    matcher = FuzzyMatcher(text_weight=0.3, number_weight=0.7, similarity_threshold=0.6)
    dup_matcher = FuzzyMatcher(text_weight=0.3, number_weight=0.7, similarity_threshold=0.649)

    table1_data = alaska_pmc.to_dict(orient='records')
    table2_data = alaska_property.to_dict(orient='records')

    
    # Create Record objects
    table1 = [matcher.create_record(row['Combined'], row) for row in table1_data]
    print("Table 1 Length: " +str(len(table1)))
    table2 = [matcher.create_record(row['Reference'], row) for row in table2_data]
    print("Table 2 Length: " +str(len(table2)))
    #table1 = [matcher.create_record(row["Invoice"], row["Combined"], row) for row in table1_data]
    #table2 = [matcher.create_record(row["id"], row["description"], row) for row in table2_data]
    
    # Find matches between tables
    matches, no_match1, no_match2 = matcher.find_matches(table1, table2)
    print(f"Total Matches Found: {len(matches)}")
    print(f"Total No Match Found: {len(no_match1)}")
    print(f"Total No Match Found: {len(no_match2)}")

    with open('output.csv', 'w') as f:
        for match in matches:
            f.write(match.to_csv() + '\n')
    #matches, no_match = matcher.find_matches(table2, table1)
    #print(f"Total Matches Found: {len(matches)}")
    #print(f"Total No Match Found: {len(no_match)}")
    #print("=== MATCHES BETWEEN TABLES ===")
    
    if verbose == True:
        for match in matches:
            print(f"Match Score: {match.similarity_score:.3f} ({match.confidence})")
            print(f"  Table1: {match.record1.description}")
            print(f"  Table2: {match.record2.description}")
            print(f"  Text Score: {match.text_score:.3f}, Number Score: {match.number_score:.3f}")
            print(f"  Numbers1: {match.record1.numbers}, Numbers2: {match.record2.numbers}")
            print()
    
    # Find duplicates within table1
    duplicates1 = dup_matcher.find_duplicates_within_table(table1)
    if verbose == True:
        if duplicates1:
            print("=== DUPLICATES WITHIN TABLE 1 ===")
            for dup in duplicates1:
                print(f"Duplicate Score: {dup.similarity_score:.3f} ({dup.confidence})")
                print(f"  Record1: {dup.record1.description}")
                print(f"  Record2: {dup.record2.description}")
                print()
            print("Duplicate Count Table 1: "+str(len(duplicates1)))
        else:
            print("No duplicates found within table 1")
    #
    # Find duplicates within table2
    #duplicates2 = dup_matcher.find_duplicates_within_table(table2)
    #
    #if verbose == True:
    #    if duplicates2:
    #        print("=== DUPLICATES WITHIN TABLE 2 ===")
    #        for dup in duplicates2:
    #            print(f"Duplicate Score: {dup.similarity_score:.3f} ({dup.confidence})")
    #            print(f"  Record1: {dup.record1.description}")
    #            print(f"  Record2: {dup.record2.description}")
    #            print()
    #        print("Duplicate Count Table 2: "+str(len(duplicates2)))    
    #    else:
    #        print("No duplicates found within table 2")
        

    ##Does not work since match object contains record1 and record2
    
    #duplicates_match = dup_matcher.find_duplicates_within_table(matches)
    #print(f"Total Matches Found: {len(duplicates_match)}")
    #if verbose == True:
    #    if duplicates_match:
    #        print("=== DUPLICATES WITHIN MATCH TABLE ===")
    #        for dup in duplicates_match:
    #            print(f"Duplicate Score: {dup.similarity_score:.3f} ({dup.confidence})")
    #            print(f"  Record1: {dup.record1.description}")
    #            print(f"  Record2: {dup.record2.description}")
    #            print()
    #    else:
    #        print("No duplicates found within match table")
#
    #duplicates_nomatch = dup_matcher.find_duplicates_within_table(no_match)
    #print(f"Total No Match Found: {len(duplicates_nomatch)}")
    #if verbose == True:
    #    if duplicates_nomatch:
    #        print("=== DUPLICATES WITHIN NO MATCH TABLE ===")
    #        for dup in duplicates_nomatch:
    #            print(f"Duplicate Score: {dup.similarity_score:.3f} ({dup.confidence})")
    #            print(f"  Record1: {dup.record1.description}")
    #            print(f"  Record2: {dup.record2.description}")
    #            print()
    #    else:
    #        print("No duplicates found within no match table")
    #        