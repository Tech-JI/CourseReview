# API Information 

## https://coursesel.umji.sjtu.edu.cn/jdji/tpm/findOwnCollegeCourse_JiCourse.action

### Data Fields
- `courseCode`
- `courseId`
- `courseName`
- `courseNameEn`
- `courseTypeId`
- `credit`
- `hour`
- `isCompulsory`
- `status`

### Sample Response
```json
[
    {
        "courseAttribute": 0,
        "courseCatalog": "",
        "courseCategory": "CourseCategory.2",
        "courseCode": "ECE3300J",
        "courseId": "008697DB-3EE0-4330-8787-A4169688C039",
        "courseName": "电磁学（2）",
        "courseNameEn": "Electromagnetics II",
        "courseTypeId": "86572329-1D6E-469F-AD25-DCEDDCC85F08",
        "courseTypeName": "",
        "credit": "4",
        "creditOuter": "0",
        "crossTerm": 0,
        "departmentIds": "",
        "departmentNames": "",
        "departments": [],
        "description": "Standard Course Profile Form-Ve330.pdf",
        "experimentHour": "",
        "faceTeachingHour": "",
        "hour": "60",
        "isCompulsory": 0,
        "language": "en_US",
        "lastUpdateDate": "2017-10-27 15:35:00",
        "lastUpdateUserId": "DFF3D5F4-65C6-462C-A2E3-559FDB2FA2E2",
        "memo": "",
        "prerequisiteCourseCount": "",
        "retakeStudyScore": 66,
        "selfStudyHour": "",
        "shortName": "ECE3300J",
        "status": 1,
        "teacherId": "",
        "teacherName": ""
    },
    {
        "courseAttribute": 0,
        "courseCatalog": "",
        "courseCategory": "CourseCategory.3",
        "courseCode": "ENGL1530J",
        "courseId": "00EF66A8-DA13-42C4-892C-DD9A103E1058",
        "courseName": "从小说到电影",
        "courseNameEn": "Novel into Film",
        "courseTypeId": "91EB55FA-20DF-4E04-9402-1B33A19BA55C",
        "courseTypeName": "",
        "credit": "3",
        "creditOuter": "",
        "crossTerm": 0,
        "departmentIds": "",
        "departmentNames": "",
        "departments": [],
        "description": "",
        "experimentHour": "",
        "faceTeachingHour": "",
        "hour": "45",
        "isCompulsory": 0,
        "language": "en_US",
        "lastUpdateDate": "2019-04-16 14:39:50",
        "lastUpdateUserId": "DFF3D5F4-65C6-462C-A2E3-559FDB2FA2E2",
        "memo": "",
        "prerequisiteCourseCount": "",
        "retakeStudyScore": 66,
        "selfStudyHour": "",
        "shortName": "ENGL1530J",
        "status": 1,
        "teacherId": "",
        "teacherName": ""
    },
    {
        "courseAttribute": 0,
        "courseCatalog": "",
        "courseCategory": "CourseCategory.3",
        "courseCode": "VR354",
        "courseId": "02120A79-97ED-45B1-91E3-F1A0F473E910",
        "courseName": "认知心理学概论",
        "courseNameEn": "Introduction to Cognitive Psychology",
        "courseTypeId": "A54CA3AF-E010-4ABA-B89C-F19AF0E77333",
        "courseTypeName": "",
        "credit": "3",
        "creditOuter": "3",
        "crossTerm": 0,
        "departmentIds": "",
        "departmentNames": "",
        "departments": [],
        "description": "This course provides students with an overview of cognitive psychology...",
        "experimentHour": "",
        "faceTeachingHour": "",
        "hour": "48",
        "isCompulsory": 0,
        "language": "en_US",
        "lastUpdateDate": "2020-07-28 15:27:50",
        "lastUpdateUserId": "11084",
        "memo": "",
        "prerequisiteCourseCount": "",
        "retakeStudyScore": 66,
        "selfStudyHour": "",
        "shortName": "VR354",
        "status": 1,
        "teacherId": "",
        "teacherName": ""
    }
]
```


## https://coursesel.umji.sjtu.edu.cn/tpm/findAll_PrerequisiteCourse.action

### Data Fields
- courseId
- prerequisiteRule
- prerequisiteRuleDesc

### Sample Response
```json
[
    {
      "courseId": "34F27950-50E7-4D4C-9321-2559FDE2B575",
      "lastUpdateDate": "2018-04-18 16:46:48",
      "lastUpdateUserId": "60366",
      "prerequisiteCourseId": "38CC7A6A-5495-435B-A5AA-9534BED228CD",
      "prerequisiteRule": [
        { "type": "symbol", "symbol": "(" },
        {
          "type": "course",
          "courseId": "561BE836-4EAC-440E-B066-C457A3AA9AE2",
          "courseName": "微分方程",
          "courseCode": "MATH2160J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": "||" },
        {
          "type": "course",
          "courseId": "F7AF87CF-7503-4368-83A9-6548B0C50825",
          "courseName": "线性代数和微分方程A",
          "courseCode": "MATH2560J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": "||" },
        {
          "type": "course",
          "courseId": "5C590497-E3FA-4128-96EF-7DC8083B43CB",
          "courseName": "线性代数和微分方程B",
          "courseCode": "MATH2860J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": ")" },
        { "type": "symbol", "symbol": "&&" },
        { "type": "symbol", "symbol": "(" },
        {
          "type": "course",
          "courseId": "E7070CAD-2453-45EC-B569-7FE117A97C20",
          "courseName": "普通物理（2）",
          "courseCode": "PHYS2400J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": "||" },
        {
          "type": "course",
          "courseId": "5E36E16A-FC86-4F1A-99B0-1C022629A584",
          "courseName": "强化物理（J类）（2）",
          "courseCode": "PHYS2600J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": ")" }
      ],
      "prerequisiteRuleDesc": "(MATH2160J 已获学分 || MATH2560J 已获学分 || MATH2860J 已获学分) && (PHYS2400J 已获学分 || PHYS2600J 已获学分)"
    },
    {
      "courseId": "1D8EC601-290F-4DBD-A26C-F93D28CFBE3A",
      "lastUpdateDate": "2018-04-18 16:44:38",
      "lastUpdateUserId": "60366",
      "prerequisiteCourseId": "377474C3-DC59-4A09-95FD-4F0915AFF437",
      "prerequisiteRule": [
        {
          "type": "course",
          "courseId": "78796516-F909-4A3E-A974-897F746BF6CB",
          "courseName": "工程概率方法",
          "courseCode": "ECE4010J",
          "option": "obtainedCredit"
        }
      ],
      "prerequisiteRuleDesc": "ECE4010J 已获学分"
    },
    {
      "courseId": "EEE20D83-DC6B-4487-9327-1CB535CE5529",
      "lastUpdateDate": "2018-04-18 16:47:40",
      "lastUpdateUserId": "60366",
      "prerequisiteCourseId": "4B428104-5701-4C5F-86CE-3BE3FC16CCCF",
      "prerequisiteRule": [
        { "type": "symbol", "symbol": "(" },
        {
          "type": "course",
          "courseId": "274CB4C1-75A7-4DA1-807F-CCB9E7F8D038",
          "courseName": "线性代数",
          "courseCode": "MATH2140J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": "||" },
        {
          "type": "course",
          "courseId": "5C590497-E3FA-4128-96EF-7DC8083B43CB",
          "courseName": "线性代数和微分方程B",
          "courseCode": "MATH2860J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": ")" },
        { "type": "symbol", "symbol": "&&" },
        {
          "type": "course",
          "courseId": "78796516-F909-4A3E-A974-897F746BF6CB",
          "courseName": "工程概率方法",
          "courseCode": "ECE4010J",
          "option": "obtainedCredit"
        }
      ],
      "prerequisiteRuleDesc": "(MATH2140J 已获学分 || MATH2860J 已获学分) && ECE4010J 已获学分"
    },
    {
      "courseId": "B423A4E3-1FA2-4BC8-B99C-9FC19221CF59",
      "lastUpdateDate": "2017-04-13 17:15:57",
      "lastUpdateUserId": "5423DB2A-3C4D-4327-B6D5-0992FA888845",
      "prerequisiteCourseId": "07D4D858-B585-4F03-8ABA-814034C5AA86",
      "prerequisiteRule": [
        {
          "type": "course",
          "courseId": "C5FF8EA5-DA16-434B-A617-B63D8633A935",
          "courseName": "动态系统建模分析与控制",
          "courseCode": "ME3600J",
          "option": "obtainedCredit"
        }
      ],
      "prerequisiteRuleDesc": "ME3600J Obtained Credit"
    },
    {
      "courseId": "41586CA0-DDAF-4472-BC1C-48DE2136E7A0",
      "lastUpdateDate": "2017-05-13 22:23:08",
      "lastUpdateUserId": "60366",
      "prerequisiteCourseId": "9D9D4F00-8B7A-4E9E-83D5-5B7003475DAB",
      "prerequisiteRule": [
        {
          "type": "course",
          "courseId": "A8D68188-A2F8-47F0-BB35-37C4DEA63CE8",
          "courseName": "德语（1）",
          "courseCode": "GER1100J",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": "||" },
        {
          "type": "course",
          "courseId": "A8D68188-A2F8-47F0-BB35-37C4DEA63CE8",
          "courseName": "德语（1）",
          "courseCode": "GER1100J",
          "option": "electedCredit"
        },
        { "type": "symbol", "symbol": "||" },
        {
          "type": "course",
          "courseId": "C20025AB-E429-47AF-852A-04F6B76FABE6",
          "courseName": "德语（J类）（1）",
          "courseCode": "VW100",
          "option": "obtainedCredit"
        }
      ],
      "prerequisiteRuleDesc": "GER1100J Obtained Credit || GER1100J Credits Submitted || VW100 Obtained Credit"
    },
    {
      "courseId": "561BE836-4EAC-440E-B066-C457A3AA9AE2",
      "lastUpdateDate": "2019-05-05 16:14:47",
      "lastUpdateUserId": "F75BEDAE-8658-4FB7-BA0E-9601A9306681",
      "prerequisiteCourseId": "B8EDDD41-0578-4A4E-9DB2-2D794222054E",
      "prerequisiteRule": [
        {
          "type": "course",
          "courseId": "D6318202-699F-4B25-B793-CAEF867E2359",
          "courseName": "微积分（3）",
          "courseCode": "MATH2150J",
          "option": "obtainedCredit"
        }
      ],
      "prerequisiteRuleDesc": "MATH2150J 已获学分"
    },
    {
      "courseId": "1BCE2420-FA95-44CE-AC02-E5E16AC3454F",
      "lastUpdateDate": "2017-04-13 11:12:40",
      "lastUpdateUserId": "5423DB2A-3C4D-4327-B6D5-0992FA888845",
      "prerequisiteCourseId": "DC576796-3A7D-41CE-8C07-F7AF4BD3920C",
      "prerequisiteRule": [
        {
          "type": "course",
          "courseId": "44994CE3-A141-4E58-94CA-8B5C8AFFA3AD",
          "courseName": "工程热力学（J类）（1）",
          "courseCode": "ME2350J",
          "option": "obtainedCredit"
        }
      ],
      "prerequisiteRuleDesc": "ME2350J Obtained Credit"
    },
    {
      "courseId": "3D57A704-3FDD-4342-A683-5BCD70DE927B",
      "lastUpdateDate": "2017-03-09 16:06:49",
      "lastUpdateUserId": "ADMIN",
      "prerequisiteCourseId": "38332DB6-E296-4BC5-B115-56F7687F0203",
      "prerequisiteRule": [
        {
          "type": "course",
          "courseId": "447EBC94-5794-53FA-E050-A8C0190176B5",
          "courseName": "计算流体力学（英文班）",
          "courseCode": "EP26002",
          "option": "obtainedCredit"
        },
        { "type": "symbol", "symbol": "<" },
        { "type": "input", "value": "5" }
      ],
      "prerequisiteRuleDesc": "EP26002 Obtained Credit < 5"
    }
]
```

## https://coursesel.umji.sjtu.edu.cn/tpm/findLessonTasksPreview_ElectTurn.action

### Data Fields
- electTurn
- courseType
- lessonTask
