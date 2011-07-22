import os, sys 
from optparse import OptionParser

from ..logger import logger
from ..filesystem_utils import locate
from ..io import saccades_read_h5 
import traceback
import flydra_db

description = """ 
    Puts the data generated by geo_sac_Detect in a FlydraDB.
    
    Usage:
    
        %s --db <flydra_db>   <directory>
        
        directory: the directory used by FlydraDB
        
    Returns:
    
         0   on success
        -1   for wrong configuration/usage
        -2   for other errors
""" % sys.argv[0]


def main():
    parser = OptionParser(usage=description)
    parser.add_option("--db", help="FlydraDB directory") 
        
    (options, args) = parser.parse_args() #@UnusedVariable

    try:    
        if options.db is None:
            raise Exception('Please provide --db option')
        
        if len(args) != 1:
            raise Exception('Please provide exactly one argument.')
   
    except Exception as e:
        logger.error('Error while parsing configuration.')
        logger.error(str(e))
        sys.exit(-1)

    # detection parameters
    directory = args[0]
    
    try:
            
        if not os.path.exists(directory):
            raise Exception('Directory %r does not exist.' % directory)
    
        pattern = '*-saccades.h5'
        
        logger.info('Looking for files with pattern %r in directory %r.' % 
                    (pattern, directory))
        
        files = sorted(list(locate(pattern=pattern, root=directory)))
        
        if not files:
            raise Exception('No files with pattern %r found in directory %r ' % \
                            (pattern, directory))
        
        logger.info('Found %d files.' % len(files))
        
        
        with flydra_db.safe_flydra_db_open(options.db, create=True) as db:
            for i, file in enumerate(files):
                saccades = saccades_read_h5(file)
                saccades['sample_num'] = i
                logger.debug('Sample %s: %d saccades.' % (file, len(saccades)))
                store_sample_in_flydra_db(saccades, db)

    
    except Exception as e:
        logger.error('Error while processing. Exception and traceback follow.')
        logger.error(str(e))
        logger.error(traceback.format_exc())
        sys.exit(-2)


def store_sample_in_flydra_db(saccades, db):         
    # get all attributes from the first saccade
    saccade = saccades[0]
    
    # sample name
    sample = saccade['sample']
    
    # the groups for this samples
    groups = []
    # add the stimulus as a group
    groups.append(saccade['stimulus'])
    
    # add "posts" if not nopost
    if saccade['stimulus'] != 'nopost':
        groups.append('posts')

    # attributes
    attrs = {
             'stimulus': saccade['stimulus'],
             'species': saccade['species'],
             'processed': saccade['processed'],
    }
    
    if not db.has_sample(sample):
        db.add_sample(sample)
        
    db.set_table(sample, 'saccades', saccades)
    
    for group in groups:
        db.add_sample_to_group(sample, group)
        
    for k, v in attrs.items():
        db.set_attr(sample, k, v)
    
    print('Groups: %r' % db.list_groups_for_sample(sample))
    
    
        