from enum import Enum


class LapInfoClassificationTypeString(str, Enum):
    HANDICAP = "Handicap"
    POINTMERGE = "PointMerge"
    PRACTICEANDQUALIFICATION = "PracticeAndQualification"
    QUALIFICATIONMERGE = "QualificationMerge"
    RACE = "Race"
    RACEMERGE = "RaceMerge"
    TIMETRIAL = "Timetrial"

    def __str__(self) -> str:
        return str(self.value)
