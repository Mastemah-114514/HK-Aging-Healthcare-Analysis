import arcpy
import pandas as pd
import math
import os

# Task 2: Python Module Implementation for Facilities
# This module is used to read cleaned data of different facilities, convert it into ArcGIS feature classes, and perform simple spatial location queries.
class Facility:

    # Initialization method: Receive the path to the cleaned facility CSV file and define instance variables to record core attributes.
    def __init__(self, csv_filepath):
        # csv_filepath (str): The file path of the cleaned CSV facility data.
        self.csv_filepath = csv_filepath
        try:
            self.df = pd.read_csv(csv_filepath)
        except Exception as e:
            print(f"Error: {e}")
            self.df = pd.DataFrame()
            
        # 定义实例变量记录设施位置、类型、所在行政区等属性
        # 假设您的 CSV 经过清洗后统一包含：facility_id, facility_name_en, latitude, longitude, district, facility_type
        if not self.df.empty:
            self.facility_type = self.df.get('facility_type', pd.Series(['Unknown_Facility'])).iloc[0]
            self.locations = list(zip(self.df['latitude'], self.df['longitude']))
            self.districts = self.df['district'].unique().tolist()
            self.records = self.df.to_dict('records')
            print(f"Successfully loaded {len(self.records)} {self.facility_type} facilities.")
        else:
            self.facility_type = "Unknown_Facility"
            self.locations = []
            self.districts = []
            self.records = []
            print("警告：加载的数据集为空。")


    def bind_capacity_data(self, capacity_csv_filepath):
        """
        【自定义拓展功能】：绑定设施容量和需求数据
        作用：由于后续Task 3需要分析设施床位缺口，这里提前提供基础提取功能，
             将官方分区床位数容量等信息与我们自身的设施类绑定。
             
        参数:
            capacity_csv_filepath (str): 官方的分区容量/需求数据表路径
        """
        print("开始绑定设施分区容量指标...")
        try:
            cap_df = pd.read_csv(capacity_csv_filepath)
            # 假设容量表包含列 "district" 和 "bed_capacity"
            # 以行政区(district)为基准将容量数据连接至主表
            self.df = pd.merge(self.df, cap_df[['district', 'bed_capacity']], on='district', how='left')
            # 刷新记录
            self.records = self.df.to_dict('records')
            print("容量数据绑定完成！可以在后续功能中使用设施的 bed_capacity 属性。")
        except Exception as e:
            print(f"容量数据绑定失败: {e}")


    def to_feature_class(self, geodatabase_path):
        """
        方法：将加载的设施信息转换为要素类并存储到 ArcGIS 地理数据库中。
        
        参数:
            geodatabase_path (str): 目标 .gdb 地理数据库的绝对路径。
        输出:
            返回创建好的要素类的完整路径。
        """
        fc_name = f"{self.facility_type.replace(' ', '_')}_FC"
        fc_path = os.path.join(geodatabase_path, fc_name)
        
        # 开启覆盖环境以防多次运行报错
        arcpy.env.overwriteOutput = True
        
        # 创建点要素类，使用 WGS1984 坐标系 (WKID 4326)
        sr = arcpy.SpatialReference(4326)
        arcpy.management.CreateFeatureclass(geodatabase_path, fc_name, "POINT", spatial_reference=sr)
        
        # 定义要添加的字段
        fields = ['facility_id', 'facility_name_en', 'district', 'facility_type']
        
        # 如果调用过 bind_capacity_data ，就多加一个床位属性列
        if 'bed_capacity' in self.df.columns:
            fields.append('bed_capacity')

        # 在要素类中实际创建字段
        for field in fields:
            # capacity 给数值型，其他都是文本型
            field_type = "LONG" if field == "bed_capacity" else "TEXT"
            arcpy.management.AddField(fc_path, field, field_type)

        # 插入游标，插入列表第一个必须是空间几何形体标签：'SHAPE@XY'
        insert_fields = ['SHAPE@XY'] + fields
        
        with arcpy.da.InsertCursor(fc_path, insert_fields) as cursor:
            for row in self.records:
                row_values = []
                # 追加经纬度对 (longitude=X, latitude=Y)
                row_values.append((row['longitude'], row['latitude']))
                
                # 追加其他字段属性内容
                for f in fields:
                    if f == "bed_capacity":
                        # 处理空值
                        val = row.get(f)
                        row_values.append(int(val) if pd.notnull(val) else 0)
                    else:
                        row_values.append(str(row.get(f, 'N/A')))
                        
                # 将构建好的一行插入GDB中
                cursor.insertRow(row_values)
                
        print(f"要素类创建成功，已输出至: {fc_path}")
        return fc_path


    def find_nearest_facility(self, target_lat, target_lon):
        """
        方法：接收一对指定的经纬度，并返回所有记录中距离该位置最近的某个设施。
        为了确保作为作业的可读性及精简性，此处采用平面欧氏距离（Euclidean Distance）进行坐标近似计算。
        
        参数:
            target_lat (float): 目标点纬度
            target_lon (float): 目标点经度
            
        返回:
            dict: 包含最近设施英文名及其经纬度的 Python 字典对象。
        """
        if not self.records:
            print("目前没有设施数据可用于计算。")
            return None
            
        nearest_fac = None
        min_dist = float('inf')
        
        for fac in self.records:
            lat = fac['latitude']
            lon = fac['longitude']
            
            # 使用平面坐标直线性差值近似距离，简化作业计算过程
            dist = math.sqrt((lat - target_lat)**2 + (lon - target_lon)**2)
            
            if dist < min_dist:
                min_dist = dist
                nearest_fac = fac
                
        if nearest_fac:
            # 组装返回结果对象
            result = {
                'facility_name_en': nearest_fac.get('facility_name_en', 'Unknown'),
                'latitude': nearest_fac.get('latitude'),
                'longitude': nearest_fac.get('longitude'),
                'district': nearest_fac.get('district', 'Unknown'),
                'relative_distance': min_dist
            }
            return result
        return None
