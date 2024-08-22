LayupList.Web.CourseDetail = function(courseId) {
    var com = LayupList.Web.Common;
    var cd = LayupList.Web.CourseDetail;
    cd.upvote = function(courseId, element, forLayups) { com.vote(1, courseId, element, forLayups); };
    cd.downvote = function(courseId, element, forLayups) { com.vote(-1, courseId, element, forLayups); };

    $.getJSON('/api/course/' + courseId + '/professors', function(data) {
        $('#id_professor').autocomplete({
            minLength: 0,
            source: data.professors
        }).focus(function() {
            $(this).autocomplete("search", $(this).val());
        });
    });

    $.getJSON('/api/course/' + courseId + '/medians', function(data) {
        data = data.medians;
        $medianChart = $(".median-chart");
        if (data.length === 0) {
            $medianChart.remove()
            $(".median-header").remove()
            return;
        }

        var margin = {top: 20, right: 20, bottom: 30, left: 40},
            width = $medianChart.width() - margin.left - margin.right,
            height = 250 - margin.top - margin.bottom;

        var x = d3.scale.ordinal().rangeRoundBands([0, width], 0.1);
        var y = d3.scale.linear().range([height, 0]);
        var xAxis = d3.svg.axis().scale(x).orient("bottom");
        var yAxis = d3.svg.axis().scale(y).orient("left").tickFormat(function(d) {
            if (d == 12)  return "A";
            else if (d == 11) return "A-";
            else if (d == 10) return "B+";
            else if (d == 9) return "B";
            else if (d == 8) return "B-";
            else if (d == 7) return "C+";
            else if (d == 6) return "C";
            else if (d == 5) return "C-";
            else if (d == 4) return "";
            else if (d == 3) return "D";
            else return "";
        }).tickValues([3,4,5,6,7,8,9,10,11,12]);

        var svg = d3.select(".median-chart").append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        x.domain(data.map(function(d) { return d.term; }));
        y.domain([3, 12]);

        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .call(xAxis);

        svg.append("g")
            .attr("class", "y axis")
            .call(yAxis);

        svg.selectAll(".bar")
            .data(data)
            .enter().append("rect")
            .attr("class", "bar")
            .attr("x", function(d) { return x(d.term); })
            .attr("width", x.rangeBand())
            .attr("y", function(d) { return y(d.avg_numeric_value); })
            .attr("height", function(d) { return height - y(d.avg_numeric_value); });
    });
};
