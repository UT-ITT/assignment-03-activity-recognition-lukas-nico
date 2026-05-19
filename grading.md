# Lukas & Nico (11.5/15P)

## Gathering Tracking Data (5/5P)
* data is logged correctly
    * yep (2P)
* log files are named and structured appropiately 
    * yep (1P)
* logging can be started with the DIPPID device
    * yep (1P)
* enough data sets captured
    * yep (1P)

## Acticity Recognition (7.5/10P)
* the program loads training data correctly
    * yep (1P)
* training data is pre-processed appropiately
    * yep (2P)
* a classifier is trained with this training data when the program is started
    * yep (1P)
* the classifier recognizes activities correctly
    * only rowing and lifting, running sometimes, couldn't get jumpingjacks to work (1.5P)
* prediction accuracy for a test data set is printed
    * in line 120 you should use window instead of data, only then the correct accuracy is printed (0P)
* prediction works continously without requiring intervention by the user
    * yep (1P)
* the fitness training application works and displays training activities and if they are executed correctly
    * yep (1P)

## Code Quality (-1P)
* can't be stopped with 'q' nor with 'esc' (windows closes, but terminal still running) 
* fonts don't work, had to debug things